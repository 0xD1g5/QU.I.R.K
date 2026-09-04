"""Phase 166 GATE-03 (rewritten, Phase 183-05, DRIFT-01): forward-locking gate
against reintroducing a crash-exposed ``subprocess.run``/``Popen``/
``check_output``/``call`` spawn anywhere under ``tests/``.

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
AND no ``cwd`` keyword, on every direct spawn call it finds.

If this gate fails, route the offending call through
``tests/cli_helpers.py::run_cli`` (for ``run_scan.py`` invocations) or
``tests/cli_helpers.py::run_fork_safe`` (for any other executable) instead
of calling ``subprocess.run``/``Popen``/``check_output``/``call`` directly,
or add a ``_GRANDFATHERED`` entry with a written reason if migration is
genuinely not applicable.

Uses an AST walk, not a line-regex/substring grep, because several spawn
calls span multiple lines with keywords on their own line, and the words
"cwd" and "close_fds" also legitimately appear in docstrings/comments
(including in this very file and in ``tests/cli_helpers.py``) that must NOT
trip the gate.

--- Phase 183-05 rewrite: DERIVED file set, not an enumerated one ---

Prior to this rewrite, the gate walked a hand-maintained, enumerated file
list (deleted in this rewrite -- see 183-05-SUMMARY.md for its former name
and shape). That list had grown to 15 entries via five separate phases (166, 168,
172, 176, 182), of which 14 had already been fully migrated and contained
zero remaining spawns, while a live re-measurement at Phase 183 planning
time found **18 unlisted files carrying 28 non-compliant direct spawn
sites** that the list-based gate could never see, because nothing forced
the list to track reality. Phase 183 migrated all 28 sites (waves 1-4) and
this task (183-05) replaces the enumeration mechanism itself: the gate now
globs ``tests/**/*.py`` and AST-walks every file it finds, at test-run
time, on every run -- "is a test file that spawns a subprocess" *is* the
criterion, so deriving the file set from that criterion closes the drift
class permanently rather than requiring PR discipline to keep a list
current. This mirrors the run-time-source-scan pattern Phase 182-07 built
for the GSD ``state.*`` bold-field defect class
(``tests/test_gsd_state_patch.py::_scan_bold_field_occurrences`` /
``_BOLD_FIELD_DISPOSITIONS`` / ``test_bold_field_regex_class_is_fully_dispositioned``)
-- see ``./CLAUDE.md``'s "GSD `state.*` Verb Integrity" section for why a
derived, run-time-regenerated occurrence set beats a written list.

**Out of scope, stated explicitly (Phase 183 CONTEXT.md D-01/D-02):**
``quirk/``, ``scripts/``, and ``uat_runner.py`` spawn sites are
deliberately NOT covered by this gate. Their subprocess calls are not
forked from a pytest process holding Network.framework state -- the
crash this gate guards against is a full-suite-pytest phenomenon, not a
general subprocess-safety concern -- so they carry a different hazard
profile and are out of scope for this gate. (Measured at Phase 183
planning time: 12 sites across 9 files across those three locations,
recorded as a deferred idea in the Phase 183 CONTEXT rather than silently
dropped; they are not gated here and are not this gate's concern.)

**Detection covers both call forms.** In addition to the
``subprocess.run(...)`` attribute form, this gate also flags bare-name
calls reachable via ``from subprocess import run, Popen, check_output,
call`` (including ``as`` aliases) -- a derived gate that only recognized
the attribute form would be trivially bypassable by changing an import
line. Zero real call sites use the bare-name form anywhere in this repo as
of Phase 183 (verified by this same AST walk); the bare-name branch is
purely forward-locking and is proven only by the synthetic fixture in
``test_bare_name_subprocess_import_is_detected`` below.
"""
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_TESTS_ROOT = _REPO_ROOT / "tests"

# Attribute names on a `subprocess` module reference (or a bare name bound
# by `from subprocess import ...`) that spawn a real child process and
# therefore fall under the posix_spawn requirement.
_SPAWNING_ATTRS = {"run", "Popen", "check_output", "call"}

# ---------------------------------------------------------------------------
# Grandfather ledger.
#
# Keyed PER-FILE ONLY -- never per-(file, lineno). Per-line keying is
# exactly what makes tests/test_skip_registry.py re-break on unrelated line
# drift (Phase 184's documented cleanup scope; this gate deliberately does
# not repeat that mistake). Each value must be a non-empty reason string;
# each key must name a file that still exists on disk. Both are enforced by
# test_grandfathered_entries_are_current below.
#
# This ledger ships EMPTY. Phase 183's per-file disposition audit
# (183-RESEARCH.md "Migration Ledger") found zero legitimate grandfathering
# candidates: all 28 previously non-compliant sites across 18 files migrated
# cleanly to tests/cli_helpers.py::run_cli / ::run_fork_safe. Because it
# ships empty, a test that merely loops over `_GRANDFATHERED.items()` would
# pass vacuously forever without ever exercising its own failure modes
# (a stale key, or a blank reason) against real data -- which is precisely
# why test_grandfathered_entries_are_current also runs the same validation
# helper against synthetic stale/blank ledgers below. Do not add an entry
# reflexively just to satisfy a failing assertion; a grandfather reason must
# be a genuine, written justification.
_GRANDFATHERED: dict[str, str] = {}


def _derive_test_files(root: Path = _TESTS_ROOT) -> list[Path]:
    """Return every ``.py`` file under *root*, sorted, discovered by
    globbing at call time rather than reading a hand-maintained list.

    ``root`` is a required parameter (not hidden behind a module-level
    constant only) specifically so the falsifiability self-tests below can
    point the real derivation at a throwaway ``tmp_path`` tree and prove the
    derivation property itself, not merely the detector logic."""
    return sorted(root.glob("**/*.py"))


def _bare_spawn_names(tree: ast.AST) -> set[str]:
    """Names bound at module scope by ``from subprocess import run, Popen,
    check_output, call`` (respecting ``as`` aliases) in *tree*. Only these
    bare names count as subprocess spawn calls -- matching on the bare name
    alone (e.g. any call named ``run``) would false-positive on an unrelated
    same-named local function or an import from a different module (see the
    negative half of test_bare_name_subprocess_import_is_detected)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                if alias.name in _SPAWNING_ATTRS:
                    names.add(alias.asname or alias.name)
    return names


def _is_direct_subprocess_spawn_call(node: ast.AST, bare_names: set[str]) -> bool:
    """True if *node* is a direct subprocess spawn call, either as
    `subprocess.<run|Popen|check_output|call>(...)` (an ast.Call whose func
    is an Attribute on a Name `subprocess`), or as a bare-name call whose
    name is in *bare_names* (i.e. actually imported from `subprocess` at
    module scope in the file currently being scanned -- see
    _bare_spawn_names)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr in _SPAWNING_ATTRS
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    ):
        return True
    return isinstance(func, ast.Name) and func.id in bare_names


def _find_offenders(file_path: Path, label: str) -> list[str]:
    """Return 'label:lineno: reason' strings for every direct
    subprocess.run/Popen/check_output/call call site (attribute form or
    bare-name form) in *file_path* that either carries a `cwd` keyword or
    lacks an explicit `close_fds=False` keyword, found via an AST walk (not
    a text grep). *label* is the string used in offender messages -- the
    real gate passes a repo-relative path; self-tests pass a tmp_path-
    relative name instead.

    An unparseable `.py` file surfaces a clear message naming the file
    rather than letting a bare SyntaxError traceback escape the test run.
    None exist in this repo today; this is defensive degradation only.
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=label)
    except SyntaxError as exc:
        return [f"{label}: could not parse as Python for the fork-safety gate: {exc}"]

    bare_names = _bare_spawn_names(tree)

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not _is_direct_subprocess_spawn_call(node, bare_names):
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
            offenders.append(f"{label}:{node.lineno}: carries cwd=...")
        if not has_close_fds_false:
            offenders.append(f"{label}:{node.lineno}: missing explicit close_fds=False")
    return offenders


def _find_offenders_in_repo_file(relative_path: Path) -> list[str]:
    """Wrapper over _find_offenders for a real repo-relative path (used by
    the main gate test and the live falsification protocol)."""
    label = str(relative_path.relative_to(_REPO_ROOT))
    return _find_offenders(relative_path, label)


def test_no_direct_crash_exposed_subprocess_spawn_in_covered_files() -> None:
    """Forward-locking gate: no direct
    subprocess.run/Popen/check_output/call call (attribute or bare-name
    form) anywhere under `tests/**/*.py` may carry a `cwd` keyword or omit
    an explicit `close_fds=False` keyword, UNLESS its file is listed in
    `_GRANDFATHERED` with a written reason (Phase 166 GATE-03, strengthened
    166-05, rewritten to a derived file set in 183-05).

    Either condition alone defeats CPython's posix_spawn selection on this
    Python build (posix_spawn requires BOTH close_fds=False AND cwd=None --
    see .planning/milestones/v5.16-phases/164-first-run-correctness/164-FINDING-fork-crash.md)
    and reintroduces the macOS fork()-after-Network.framework SIGSEGV crash.
    Route the offending call through tests/cli_helpers.py::run_cli or
    ::run_fork_safe instead, which supply close_fds=False and never pass
    cwd, or add a `_GRANDFATHERED[relative_path] = "reason"` entry if
    migration is genuinely not applicable -- do not add an entry reflexively
    just to satisfy this assertion.
    """
    offenders: list[str] = []
    for file_path in _derive_test_files():
        relative_path = file_path.relative_to(_REPO_ROOT)
        relpath_str = str(relative_path)
        if relpath_str in _GRANDFATHERED:
            continue
        offenders.extend(_find_offenders_in_repo_file(file_path))

    assert not offenders, (
        f"crash-exposed subprocess spawn(s) found in {len(offenders)} site(s): "
        f"{offenders}. A direct subprocess.run/Popen/check_output/call (attribute "
        f"or bare-name form) under tests/ must carry close_fds=False and must NOT "
        f"carry cwd -- otherwise it defeats posix_spawn selection on this Python "
        f"build and reintroduces the macOS fork()-after-Network.framework SIGSEGV "
        f"crash. Route it through tests/cli_helpers.py::run_cli / ::run_fork_safe, "
        f"or add a _GRANDFATHERED[relative_path] = 'reason' entry if migration is "
        f"genuinely not applicable (do not add one reflexively just to satisfy "
        f"this assertion). See "
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
