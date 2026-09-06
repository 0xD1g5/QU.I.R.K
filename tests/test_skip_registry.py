"""Phase 41 D-03 (module origin); Phase 184 D-01/D-02/D-03/D-06 (key
redesign): CI gate meta-test that fails when an unregistered
``pytest.skip`` / ``pytest.importorskip`` / ``@pytest.mark.skipif`` /
``@pytest.mark.skip`` / ``@pytest.mark.xfail``
is encountered in tests/.

Mechanism: walk every ``tests/*.py`` file with ``ast.parse`` + ``ast.walk``
looking for:
  - Call nodes whose func resolves to ``pytest.skip`` or ``pytest.importorskip``
  - Decorator nodes whose func resolves to ``pytest.mark.skipif``,
    ``pytest.mark.skip``, or ``pytest.mark.xfail``

Key: ``(file, test_qualname)``, not ``(file, LINENO)``.
--------------------------------------------------------
The registry key is the dotted ``ClassDef``/``FunctionDef``/``AsyncFunctionDef``
ancestor chain enclosing the skip construct (e.g. ``"TestFoo.test_bar"``), or
the literal ``"<module>"`` for module-scope skips -- derived from the AST by
``_enclosing_qualname()``, never read off a line number. ``(file, LINENO)``
keying is DELETED here, not deprecated or kept alongside it: Phase 183
changed no skip and the unrelated-line-drift violation count went 15 -> 22
anyway, which is a gate measuring the wrong coordinate. There is no
positional-tolerance constant anywhere in this file -- a tolerance window is
a confession that the key is wrong (Phase 184 CONTEXT.md D-01).

A justification belongs to the test, not to a line.
-----------------------------------------------------
Several skip sites inside one test collapse to a single ``(file, qualname)``
key and share one reason string that must honestly cover all of them (D-02).

Rejected alternatives (D-03), recorded here so this is not re-litigated:
  - content-addressing the skip construct (a hash of its normalized source):
    a typo fix in a reason string would re-break the gate -- a worse failure
    mode than line drift.
  - per-file keying (Phase 183's ``_COVERED_FILES`` shape): too coarse. One
    file can carry both an OS-conditional skip and unrelated stubs, and one
    file-level reason covering both is how fabricated justifications get
    written.

Derivation, not a bigger list (D-06).
--------------------------------------
The "derive it, don't enumerate it" mandate this phase satisfies is carried
by this structural key plus the bidirectional rot-check (registry entries
that resolve to no skip site, D-07 below), in the lineage of
``FINGERPRINT_TITLE_ALIASES`` in ``quirk/compliance/__init__.py`` -- not by
the narrow ``pytest.importorskip``-from-``pyproject.toml`` auto-allow (D-05)
described next, which covers only a small slice of sites and is a separate,
much smaller carve-out.

The one narrow derivation in force, and why it stops there (D-04/D-05).
-------------------------------------------------------------------------
Construct census across ``tests/`` (Phase 184 CONTEXT.md ``<measurement>``):
``@pytest.mark.xfail`` 76 * ``pytest.skip`` 58 * ``@pytest.mark.skip`` 24 --
all three encode human judgement about *why* a test cannot run right now and
must stay enumerated with a real reason -- against only 14
``pytest.importorskip`` sites. That 14-of-158 ratio is why D-04 rejected
deriving the bulk of the registry away: a derivation covering ~7% of sites
would only add a second matching mechanism for a marginal size win. The
registry's rot-resistance comes from the structural key (D-01) and the
bidirectional check (D-07), not by this auto-allow, and not from shrinking
the enumerated set. The one derivation that IS in force: a
``pytest.importorskip("<mod>")`` whose module maps to a package declared in
a ``[project.optional-dependencies]`` group in ``pyproject.toml`` is
auto-allowed with no registry entry, via ``_optional_extra_modules()``,
which reads ``pyproject.toml`` at test-run time -- so removing an extra
turns its sites back into violations instead of leaving a stale entry
(D-05). Exclusion from the ``[all]`` meta-extra (``hw`` / ``api`` /
``identity``) does not change auto-allow status: those are still declared
extras. A module argument that is not a string literal (a variable, an
f-string) is never auto-allowed -- the criterion must be statically
checkable.

The registry becomes bidirectional (D-07).
---------------------------------------------
A registry entry whose ``(file, qualname)`` resolves to no skip site in
``tests/`` is a violation, named with the same ``file:qualname [category]``
specificity as an unregistered-skip violation -- an exception list that
cannot be checked against reality in both directions is how 25 orphans
built up unnoticed pre-Phase-184. ``_find_orphan_entries()`` shares
``_allowed()``'s exact comparison logic (occurrences are matched against
the ledger key the same way a real skip site is), so a regression to one
half's matching logic breaks both halves together rather than leaving one
half silently unguarded.

No xfail, no allowlist, no continue-on-error, ever (D-11).
--------------------------------------------------------------
This node carries no xfail, no allowlist, and no ``continue-on-error``,
ever: ``DEFER-172-01`` absorbed a new failure during v5.18 with nobody
noticing, because the node was already red -- a permanently-red node is
where new failures go to hide. It rides the ``Linux Full Suite`` CI job
(``pytest -q -m ""``, no ``continue-on-error``) as it already does; no new
CI wiring is needed or wanted.

This file itself contains the strings ``pytest.skip`` / ``pytest.importorskip``
/ ``pytest.mark.skipif`` only as identifiers being matched on — it is excluded
from the walk, along with ``tests/skip_registry.py``.
"""
from __future__ import annotations

import ast
import pathlib
import re
import tomllib

import pytest

from tests.skip_registry import ALLOWED_SKIPS

TESTS_DIR = pathlib.Path(__file__).resolve().parent
_PYPROJECT_PATH = TESTS_DIR.parent / "pyproject.toml"

# Files exempt from the walk: the registry itself and this gate test.
EXEMPT_FILES = {"skip_registry.py", "test_skip_registry.py"}

# Phase 184 D-05: distribution-name -> import-name overrides, needed only
# where a PyPI distribution name and its top-level import name diverge
# beyond a plain hyphen-to-underscore normalization. Each key here is
# cross-checked (test_dist_to_import_name_overrides_correspond_to_real_
# declared_distributions below) to correspond to a distribution genuinely
# declared in some pyproject.toml [project.optional-dependencies] group --
# this is a name-normalization aid, not a second allowlist.
_DIST_TO_IMPORT_NAME = {
    # PyPI distribution "python-docx" (the "docx" extras group) imports as
    # "docx", not "python_docx" -- the hyphen-to-underscore heuristic alone
    # gets this one wrong.
    "python-docx": "docx",
}

_SPECIFIER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def _distribution_name_from_specifier(spec: str) -> str | None:
    """Extract the bare distribution name from a PEP 508 requirement
    specifier string (e.g. ``"pysnmp>=7.1.0,<8"`` -> ``"pysnmp"``,
    ``"quirk-scanner[email]"`` -> ``"quirk-scanner"``), stripping any
    version operator or extras bracket. Returns None if nothing
    recognizable is found."""
    match = _SPECIFIER_NAME_RE.match(spec.strip())
    if not match:
        return None
    return match.group(0)


def _optional_extra_modules(pyproject_path: pathlib.Path = _PYPROJECT_PATH) -> set[str]:
    """Return the set of top-level import names derivable from every
    ``[project.optional-dependencies]`` group in ``pyproject_path``, read
    at call time (Phase 184 D-05) -- so a group removed from
    ``pyproject.toml`` stops being covered by this function on the very
    next call, rather than staying baked into a constant. Parameterized so
    self-tests can point it at a synthetic ``tmp_path`` pyproject.toml
    without ever mutating the real one."""
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    groups = data.get("project", {}).get("optional-dependencies", {})
    modules: set[str] = set()
    for specs in groups.values():
        for spec in specs:
            dist_name = _distribution_name_from_specifier(spec)
            if dist_name is None:
                continue
            import_name = _DIST_TO_IMPORT_NAME.get(dist_name, dist_name.replace("-", "_"))
            modules.add(import_name)
    return modules


def _is_auto_allowed_importorskip(node: ast.Call, optional_modules: set[str]) -> bool:
    """True iff ``node`` is a ``pytest.importorskip(...)`` Call whose first
    positional argument is a string literal, and whose top-level dotted
    module component names a package declared in some
    ``[project.optional-dependencies]`` group (Phase 184 D-05). A
    non-literal argument (a variable, an f-string) is never auto-allowed --
    the criterion must be statically checkable from source alone."""
    if not node.args:
        return False
    first_arg = node.args[0]
    if not (isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)):
        return False
    top_level = first_arg.value.split(".")[0]
    return top_level in optional_modules


def _allowed(
    filename: str,
    qualname: str,
    ledger: list[tuple[str, str, str, str]] = ALLOWED_SKIPS,
) -> bool:
    """Return True iff (filename, qualname) is a registered entry in
    ``ledger`` (default: the real ``ALLOWED_SKIPS``). No positional
    tolerance -- the key is structural. ``ledger`` is a parameter, not a
    hardcoded global read, so self-tests can call this against synthetic
    data -- including a pseudo-ledger built from real occurrence records,
    which is how ``_find_orphan_entries()`` below shares this exact
    comparison logic for the bidirectional half of the gate (D-07)."""
    for entry_file, entry_qualname, _category, _reason in ledger:
        if entry_file == filename and entry_qualname == qualname:
            return True
    return False


def _find_orphan_entries(
    occurrences: list[tuple[str, str, str, int]],
    ledger: list[tuple[str, str, str, str]],
) -> list[tuple[str, str, str, str]]:
    """Return every ``ledger`` entry whose ``(file, qualname)`` key matches
    no ``occurrences`` record (Phase 184 D-07). Pure function of its two
    arguments -- neither is read from a module global -- so self-tests can
    call it against synthetic occurrence/ledger data without touching the
    real registry or the real tests/ tree.

    Matching is delegated to ``_allowed()`` against a pseudo-ledger built
    from the occurrence records (same ``(file, qualname)`` shape as a real
    ledger entry), rather than a second, independently-written comparison
    -- so a regression to ``_allowed()``'s matching logic breaks this half
    of the gate too, instead of leaving it silently unguarded."""
    pseudo_ledger = [
        (fname, qualname, kind, str(lineno)) for fname, qualname, kind, lineno in occurrences
    ]
    return [entry for entry in ledger if not _allowed(entry[0], entry[1], pseudo_ledger)]


def _format_orphan(entry: tuple[str, str, str, str]) -> str:
    """Format a stale registry entry with the same ``file:qualname
    [category]`` specificity as an unregistered-skip violation (D-07)."""
    fname, qualname, category, _reason = entry
    return f"{fname}:{qualname} [{category}]"


def _is_reason_blank(entry: tuple[str, str, str, str]) -> bool:
    """True iff ``entry``'s reason string is empty or whitespace-only -- a
    violation independent of whether the entry resolves to a live skip
    site, because a reason with no content is indistinguishable from an
    entry registered merely to quiet the gate."""
    return not entry[3].strip()


def _pytest_import_names(tree: ast.Module) -> set[str]:
    """Return every local name the ``pytest`` module object is bound to in
    this module: ``"pytest"`` for a plain ``import pytest``, and/or the
    alias for each ``import pytest as X``. Derived by walking the module's
    own ``Import`` nodes at parse time -- never a hand-maintained list of
    alias strings (CR-01: a hardcoded ``base.id == "pytest"`` check is
    blind to ``import pytest as _pytest_uat``, the exact vacuous-pass
    hazard this phase's gate exists to close). Returns an empty set if the
    module never imports ``pytest`` directly (e.g. only
    ``from pytest import mark``, which is not currently used anywhere in
    this tree per CR-01's fix note -- ``from pytest import ...`` forms are
    out of scope here and would need a separate resolver if one appears)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest":
                    names.add(alias.asname or "pytest")
    return names


def _is_pytest_skip_call(node: ast.AST, pytest_names: set[str] = frozenset({"pytest"})) -> bool:
    """True if ``node`` is a Call to ``pytest.skip`` or
    ``pytest.importorskip``, where ``pytest`` may be bound to any name in
    ``pytest_names`` (default: the literal ``"pytest"``, for callers -- the
    fixture-only ``_find_target_node`` and the parametrized qualname tests
    -- that don't resolve aliases; the real gate walk in
    ``_find_skip_occurrences`` always passes the module's actual resolved
    names via ``_pytest_import_names``)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id in pytest_names and func.attr in {"skip", "importorskip"}:
            return True
    return False


def _is_pytest_mark_decorator(
    node: ast.AST, mark_name: str, pytest_names: set[str] = frozenset({"pytest"})
) -> bool:
    """True if ``node`` is ``@pytest.mark.<mark_name>(...)`` (called or
    bare), where ``pytest`` may be bound to any name in ``pytest_names``
    (default: the literal ``"pytest"``; see ``_is_pytest_skip_call``)."""
    # Decorator can be either a Call (with args) or a plain Attribute access.
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and target.attr == mark_name:
        # target.value should be ast.Attribute pytest.mark
        inner = target.value
        if isinstance(inner, ast.Attribute) and inner.attr == "mark":
            base = inner.value
            if isinstance(base, ast.Name) and base.id in pytest_names:
                return True
    return False


def _enclosing_qualname(tree: ast.Module, target: ast.AST) -> str:
    """Return the dotted ``ClassDef``/``FunctionDef``/``AsyncFunctionDef``
    ancestor chain enclosing ``target`` (e.g. ``"TestFoo.test_bar"``), or the
    literal ``"<module>"`` when the chain is empty.

    Built via a parent-pointer walk over ``tree``, not a backward line-text
    scan -- Python's AST already gives exact nesting, unlike the text-scan
    technique tests/test_gsd_state_patch.py needs for un-parsed JS. A pure
    function of ``(tree, target)`` with no module-global state, so it can be
    called directly against ``tmp_path`` fixtures in self-tests.

    A decorator node's chain includes the ``FunctionDef``/``ClassDef`` it
    decorates: the decorator lives in that node's ``decorator_list``, so the
    parent-pointer walk finds it there -- not ``"<module>"``, which would
    otherwise collide with genuine module-scope skips (Phase 184 CONTEXT.md
    D-01, T-184-04).
    """
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    chain: list[str] = []
    node: ast.AST = target
    while id(node) in parents:
        node = parents[id(node)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chain.append(node.name)
    return ".".join(reversed(chain)) if chain else "<module>"


def _find_target_node(tree: ast.Module) -> ast.AST:
    """Locate the single skip-related node in a small test fixture: either a
    ``pytest.skip``/``pytest.importorskip`` Call, or the first
    ``@pytest.mark.{skip,skipif,xfail}`` decorator. Test-only helper for the
    parametrized cases below -- reuses the same detector functions the real
    gate walk uses, so the fixture and the gate agree on what a "skip
    construct" is.
    """
    pytest_names = _pytest_import_names(tree) or {"pytest"}
    for node in ast.walk(tree):
        if _is_pytest_skip_call(node, pytest_names):
            return node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for deco in node.decorator_list:
                for mark_name in ("skipif", "skip", "xfail"):
                    if _is_pytest_mark_decorator(deco, mark_name, pytest_names):
                        return deco
    raise AssertionError("no skip-related node found in fixture source")


@pytest.mark.parametrize(
    "source,expected",
    [
        pytest.param(
            "import pytest\n\n\ndef test_bar():\n    pytest.skip('x')\n",
            "test_bar",
            id="module-scope-function",
        ),
        pytest.param(
            "import pytest\n\n\nclass TestFoo:\n    def test_bar(self):\n        pytest.skip('x')\n",
            "TestFoo.test_bar",
            id="class-scoped-method",
        ),
        pytest.param(
            "import pytest\n\n\ndef test_bar():\n    def inner():\n        pytest.skip('x')\n    inner()\n",
            "test_bar.inner",
            id="nested-function",
        ),
        pytest.param(
            "import pytest\n\npytest.importorskip('foo')\n",
            "<module>",
            id="module-scope-no-enclosing-def",
        ),
        pytest.param(
            "import pytest\n\n\nasync def test_baz():\n    pytest.skip('x')\n",
            "test_baz",
            id="async-function",
        ),
        pytest.param(
            "import pytest\n\n\n@pytest.mark.skip(reason='x')\ndef test_bar():\n    pass\n",
            "test_bar",
            id="decorator-keys-to-decorated-function",
        ),
    ],
)
def test_enclosing_qualname_derives_the_ancestor_chain(source: str, expected: str) -> None:
    """Phase 184 CONTEXT.md D-01: the registry key is a structural qualname
    chain derived from the AST, not a line number. Locks
    ``_enclosing_qualname()``'s behavior across module scope, class scope,
    nested functions, async defs, and the decorator case (T-184-04: a
    decorator must key to the construct it decorates, not to ``<module>``).
    """
    tree = ast.parse(source)
    target = _find_target_node(tree)
    assert _enclosing_qualname(tree, target) == expected


def _find_skip_occurrences(
    root: pathlib.Path = TESTS_DIR,
    optional_modules: set[str] | None = None,
) -> list[tuple[str, str, str, int]]:
    """Walk every ``root/*.py`` file (except EXEMPT_FILES) and return every
    skip-style occurrence as ``(filename, qualname, kind, lineno)``.

    Pure function of ``root`` -- parameterized so self-tests can point it at
    a ``tmp_path`` fixture instead of the real tests/ directory, following
    ``tests/test_cli_helper_usage.py``'s ``_derive_test_files()`` discipline.
    ``lineno`` is retained only for human-readable failure messages; it does
    not participate in registry matching.

    A ``pytest.importorskip(...)`` occurrence whose module is auto-allowed
    per ``_is_auto_allowed_importorskip()`` (Phase 184 D-05) is excluded
    from the returned list entirely -- both from the unregistered-skip
    violation check AND from the set the bidirectional orphan check matches
    against, so an existing registry entry covering ONLY an auto-allowed
    site becomes an orphan and is retired, rather than left as a stale
    duplicate of a criterion the gate now derives for itself.
    ``optional_modules`` defaults to ``_optional_extra_modules()`` (the real
    pyproject.toml, read once per call); self-tests can pass an explicit set
    to avoid re-reading the real file.

    CR-01: ``pytest``'s local binding is resolved per-file via
    ``_pytest_import_names()`` rather than assumed to be the literal
    ``"pytest"`` -- a module that does ``import pytest as X`` is walked
    using ``{"X"}`` (or ``{"pytest"}`` if the module also does a plain
    ``import pytest`` elsewhere) as the recognized base name(s), so an
    aliased skip construct is visible to this walk exactly like an
    unaliased one.
    """
    if optional_modules is None:
        optional_modules = _optional_extra_modules()

    occurrences: list[tuple[str, str, str, int]] = []

    for py_file in sorted(root.rglob("*.py")):
        if py_file.name in EXEMPT_FILES:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, OSError):
            continue

        pytest_names = _pytest_import_names(tree)
        if not pytest_names:
            # This module never binds `pytest` to any local name -- it
            # cannot contain a pytest.skip/importorskip Call or
            # pytest.mark.* decorator, so there is nothing to walk for.
            continue

        for node in ast.walk(tree):
            # 1. Direct calls: pytest.skip(...) / pytest.importorskip(...)
            if _is_pytest_skip_call(node, pytest_names):
                func = node.func
                attr = func.attr if isinstance(func, ast.Attribute) else "?"
                if attr == "importorskip" and _is_auto_allowed_importorskip(
                    node, optional_modules
                ):
                    continue
                qualname = _enclosing_qualname(tree, node)
                occurrences.append((py_file.name, qualname, f"pytest.{attr}", node.lineno))

            # 2. Decorators on functions/classes: @pytest.mark.{skipif,skip,xfail}(...)
            decorators: list[ast.AST] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decorators = list(node.decorator_list)
            for deco in decorators:
                for mark_name in ("skipif", "skip", "xfail"):
                    if _is_pytest_mark_decorator(deco, mark_name, pytest_names):
                        qualname = _enclosing_qualname(tree, deco)
                        occurrences.append(
                            (py_file.name, qualname, f"@pytest.mark.{mark_name}", deco.lineno)
                        )

    return occurrences


@pytest.mark.skip_registry_gate
def test_no_unregistered_skips() -> None:
    """Every pytest skip-style marker in tests/ must be in ALLOWED_SKIPS,
    keyed by ``(file, qualname)`` per Phase 184 D-01 -- AND the registry
    must not carry stale rows: an entry resolving to no live skip site
    (D-07) or with an empty/whitespace-only reason is also a failure of
    this node."""
    occurrences = _find_skip_occurrences()
    violations = [
        occurrence for occurrence in occurrences if not _allowed(occurrence[0], occurrence[1])
    ]

    if violations:
        formatted = "\n".join(
            f"  {fname}:{qualname} [{kind}] (line {lineno})"
            for fname, qualname, kind, lineno in violations
        )
        pytest.fail(
            "Unregistered skip markers found (add to tests/skip_registry.py "
            "ALLOWED_SKIPS by (file, qualname) or delete the marker per "
            "Phase 184 D-01/D-09):\n"
            f"{formatted}"
        )

    orphans = _find_orphan_entries(occurrences, ALLOWED_SKIPS)
    if orphans:
        formatted_orphans = "\n".join(_format_orphan(entry) for entry in orphans)
        pytest.fail(
            "Stale registry entries found -- these resolve to no skip site "
            "anywhere in tests/ (Phase 184 D-07). A stale allowlist row is "
            "how a gate quietly stops gating anything: remove these from "
            "tests/skip_registry.py ALLOWED_SKIPS:\n"
            f"{formatted_orphans}"
        )

    blank_reason_entries = [entry for entry in ALLOWED_SKIPS if _is_reason_blank(entry)]
    if blank_reason_entries:
        formatted_blank = "\n".join(_format_orphan(entry) for entry in blank_reason_entries)
        pytest.fail(
            "Registry entries with an empty or whitespace-only reason "
            "found -- an entry with no justification is indistinguishable "
            "from one registered merely to quiet the gate:\n"
            f"{formatted_blank}"
        )


def _write_synthetic_pyproject(tmp_path: pathlib.Path, groups_toml: str) -> pathlib.Path:
    """Write a minimal synthetic pyproject.toml with the given
    ``[project.optional-dependencies]`` body into ``tmp_path`` and return
    its path -- the real pyproject.toml is never touched by these tests."""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        '[project]\nname = "quirk-scanner"\n\n'
        f"[project.optional-dependencies]\n{groups_toml}",
        encoding="utf-8",
    )
    return pyproject_path


def _importorskip_call_node(source: str) -> ast.Call:
    """Parse ``source`` and return the last statement's Call node -- a
    small test-only helper for building synthetic ``pytest.importorskip``
    Call nodes without duplicating the gate's own AST-walking logic."""
    tree = ast.parse(source)
    return tree.body[-1].value  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "groups_toml,importorskip_source,expected",
    [
        pytest.param(
            'hw = ["pysnmp>=7.1.0,<8"]\n',
            "import pytest\npytest.importorskip('pysnmp')\n",
            True,
            id="pysnmp-in-hw-group-auto-allowed",
        ),
        pytest.param(
            'docx = ["python-docx>=1.1.0"]\n',
            "import pytest\npytest.importorskip('docx')\n",
            True,
            id="docx-maps-to-python-docx-auto-allowed",
        ),
        pytest.param(
            'docx = ["python-docx>=1.1.0"]\n',
            "import pytest\npytest.importorskip('json')\n",
            False,
            id="stdlib-module-in-no-declared-extra-not-auto-allowed",
        ),
        pytest.param(
            "",
            "import pytest\npytest.importorskip('docx')\n",
            False,
            id="removing-the-group-reverts-a-previously-allowed-module",
        ),
        pytest.param(
            'identity = ["impacket>=0.13.0,<0.14"]\n'
            'all = ["quirk-scanner[cbom]"]\n',
            "import pytest\npytest.importorskip('impacket')\n",
            True,
            id="identity-excluded-from-all-still-auto-allowed",
        ),
        pytest.param(
            'hw = ["pysnmp>=7.1.0,<8"]\n',
            "import pytest\nmod_name = 'pysnmp'\npytest.importorskip(mod_name)\n",
            False,
            id="non-literal-argument-never-auto-allowed",
        ),
    ],
)
def test_importorskip_derivation_reads_pyproject_at_run_time(
    tmp_path: pathlib.Path, groups_toml: str, importorskip_source: str, expected: bool
) -> None:
    """Phase 184 CONTEXT.md D-04/D-05: the bulk of the registry is
    deliberately NOT derived away (76 xfail + 58 pytest.skip + 24 mark.skip
    encode judgement, against only 14 importorskip sites) -- the one narrow
    derivation in force reads its criterion from pyproject.toml at
    test-run time via a synthetic ``tmp_path`` file, never a baked-in
    constant, and never by mutating the real pyproject.toml."""
    pyproject_path = _write_synthetic_pyproject(tmp_path, groups_toml)
    modules = _optional_extra_modules(pyproject_path)
    call_node = _importorskip_call_node(importorskip_source)
    assert _is_auto_allowed_importorskip(call_node, modules) is expected


def test_dist_to_import_name_overrides_correspond_to_real_declared_distributions() -> None:
    """Every ``_DIST_TO_IMPORT_NAME`` key must be a distribution genuinely
    declared in some real pyproject.toml [project.optional-dependencies]
    group -- this dict is a name-normalization aid, not a second allowlist
    (Phase 184 CONTEXT.md D-05)."""
    with _PYPROJECT_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    groups = data.get("project", {}).get("optional-dependencies", {})
    declared_dist_names = {
        _distribution_name_from_specifier(spec) for specs in groups.values() for spec in specs
    }
    for dist_name in _DIST_TO_IMPORT_NAME:
        assert dist_name in declared_dist_names


@pytest.mark.parametrize(
    "case_id",
    [
        "one-orphan-entry-is-returned",
        "fully-matching-ledger-yields-empty",
        "orphan-message-formatting-matches-unregistered-skip-specificity",
        "blank-reason-is-flagged-independent-of-resolution",
        "real-ledger-against-real-tests-tree-has-zero-orphans",
    ],
)
def test_orphan_detection_flags_a_ledger_entry_that_resolves_to_nothing(case_id: str) -> None:
    """Phase 184 CONTEXT.md D-07: the registry gate is bidirectional -- an
    entry whose (file, qualname) key matches no live skip site is a
    violation, formatted with the same ``file:qualname [category]``
    specificity as an unregistered-skip violation. Five behaviors,
    parametrized as separate collected cases, using synthetic
    occurrence/ledger data so this half is proven even while the real
    ledger carries zero orphans (the fifth case)."""
    real_occurrence = ("test_real_file.py", "test_real", "pytest.skip", 10)
    matching_entry = ("test_real_file.py", "test_real", "optional_extra", "reason")
    orphan_entry = ("test_nowhere.py", "test_ghost", "optional_extra", "reason")

    if case_id == "one-orphan-entry-is-returned":
        orphans = _find_orphan_entries([real_occurrence], [matching_entry, orphan_entry])
        assert orphans == [orphan_entry]

    elif case_id == "fully-matching-ledger-yields-empty":
        orphans = _find_orphan_entries([real_occurrence], [matching_entry])
        assert orphans == []

    elif case_id == "orphan-message-formatting-matches-unregistered-skip-specificity":
        assert _format_orphan(orphan_entry) == "test_nowhere.py:test_ghost [optional_extra]"

    elif case_id == "blank-reason-is-flagged-independent-of-resolution":
        assert _is_reason_blank((*matching_entry[:3], "")) is True
        assert _is_reason_blank((*matching_entry[:3], "   ")) is True
        assert _is_reason_blank(matching_entry) is False

    elif case_id == "real-ledger-against-real-tests-tree-has-zero-orphans":
        assert _find_orphan_entries(_find_skip_occurrences(), ALLOWED_SKIPS) == []

    else:  # pragma: no cover -- defensive, keeps the parametrize list honest
        raise AssertionError(f"unhandled case_id: {case_id}")


def test_synthetic_unregistered_skip_makes_the_gate_red(tmp_path: pathlib.Path) -> None:
    """Phase 184 CONTEXT.md D-12(a): falsifiability is proven by a
    permanent self-test, not a one-time manual inject-and-revert. A
    synthetic, unregistered ``pytest.skip`` written into a ``tmp_path``
    test file -- reusing the name of a REAL registered file
    (test_broker_scanner_kafka.py) so this self-test is sensitive to a
    filename-only matching regression, not just a "new file" regression --
    must make the REAL detector (``_find_skip_occurrences`` called directly
    against ``root=tmp_path``, matched by the REAL ``_allowed()``) report
    exactly one violation naming the offending test and file. Never a
    duplicate re-implementation of the walk."""
    synthetic_file = tmp_path / "test_broker_scanner_kafka.py"
    synthetic_file.write_text(
        "import pytest\n\n\ndef test_synthetic():\n"
        "    pytest.skip('injected for falsifiability proof')\n",
        encoding="utf-8",
    )
    occurrences = _find_skip_occurrences(root=tmp_path)
    violations = [o for o in occurrences if not _allowed(o[0], o[1])]

    assert len(violations) == 1
    fname, qualname, kind, _lineno = violations[0]
    assert fname == "test_broker_scanner_kafka.py"
    assert qualname == "test_synthetic"
    assert kind == "pytest.skip"


def test_synthetic_orphan_entry_makes_the_bidirectional_half_red() -> None:
    """Phase 184 CONTEXT.md D-12(b): a synthetic ledger entry that resolves
    to no real skip site must be reported as an orphan by the REAL detector
    pair -- ``_find_skip_occurrences()`` against the real tests/ tree,
    matched by the REAL ``_find_orphan_entries()``, never a duplicate
    re-implementation. The orphan entry reuses a REAL file that DOES have a
    real occurrence (test_broker_scanner_kafka.py) under a fabricated
    qualname, so this self-test is sensitive to a filename-only matching
    regression, not merely to an unrecognized filename."""
    orphan_entry = (
        "test_broker_scanner_kafka.py",
        "TestNothing.test_nothing",
        "optional_extra",
        "injected for falsifiability proof",
    )
    ledger = list(ALLOWED_SKIPS) + [orphan_entry]

    orphans = _find_orphan_entries(_find_skip_occurrences(), ledger)

    assert orphan_entry in orphans


def test_renaming_the_enclosing_test_makes_a_registered_skip_red(tmp_path: pathlib.Path) -> None:
    """Phase 184 CONTEXT.md D-12(c): the registry key is the qualname, not
    merely the file -- proving this requires showing that a RENAME alone
    (no change to the skip construct itself) flips the violation outcome.
    This is intended behaviour, not a defect: renaming a test is a real
    change to what is being skipped, and the registered justification
    deserves re-review under the new name rather than silently carrying
    over to a differently-named test that nobody actually re-reviewed."""
    ledger = [("test_rename_fixture.py", "test_original_name", "optional_extra", "synthetic")]

    original_dir = tmp_path / "original"
    original_dir.mkdir()
    (original_dir / "test_rename_fixture.py").write_text(
        "import pytest\n\n\ndef test_original_name():\n    pytest.skip('x')\n",
        encoding="utf-8",
    )
    original_occurrences = _find_skip_occurrences(root=original_dir)
    original_violations = [
        o for o in original_occurrences if not _allowed(o[0], o[1], ledger)
    ]
    assert original_violations == []

    renamed_dir = tmp_path / "renamed"
    renamed_dir.mkdir()
    (renamed_dir / "test_rename_fixture.py").write_text(
        "import pytest\n\n\ndef test_renamed_name():\n    pytest.skip('x')\n",
        encoding="utf-8",
    )
    renamed_occurrences = _find_skip_occurrences(root=renamed_dir)
    renamed_violations = [o for o in renamed_occurrences if not _allowed(o[0], o[1], ledger)]

    assert len(renamed_violations) == 1
    assert renamed_violations[0][1] == "test_renamed_name"
