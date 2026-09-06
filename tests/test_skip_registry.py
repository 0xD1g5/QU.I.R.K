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
by this structural key plus the bidirectional rot-check landing in a later
plan (registry entries that resolve to no skip site), in the lineage of
``FINGERPRINT_TITLE_ALIASES`` in ``quirk/compliance/__init__.py`` -- not by
the narrow ``pytest.importorskip``-from-``pyproject.toml`` auto-allow (D-05),
which covers only a small slice of sites and is a separate, much smaller
carve-out.

This file itself contains the strings ``pytest.skip`` / ``pytest.importorskip``
/ ``pytest.mark.skipif`` only as identifiers being matched on — it is excluded
from the walk, along with ``tests/skip_registry.py``.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from tests.skip_registry import ALLOWED_SKIPS

TESTS_DIR = pathlib.Path(__file__).resolve().parent

# Files exempt from the walk: the registry itself and this gate test.
EXEMPT_FILES = {"skip_registry.py", "test_skip_registry.py"}


def _allowed(filename: str, qualname: str) -> bool:
    """Return True iff (filename, qualname) is a registered entry in
    ALLOWED_SKIPS. No positional tolerance -- the key is structural."""
    for entry_file, entry_qualname, _category, _reason in ALLOWED_SKIPS:
        if entry_file == filename and entry_qualname == qualname:
            return True
    return False


def _is_pytest_skip_call(node: ast.AST) -> bool:
    """True if ``node`` is a Call to ``pytest.skip`` or ``pytest.importorskip``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "pytest" and func.attr in {"skip", "importorskip"}:
            return True
    return False


def _is_pytest_mark_decorator(node: ast.AST, mark_name: str) -> bool:
    """True if ``node`` is ``@pytest.mark.<mark_name>(...)`` (called or bare)."""
    # Decorator can be either a Call (with args) or a plain Attribute access.
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and target.attr == mark_name:
        # target.value should be ast.Attribute pytest.mark
        inner = target.value
        if isinstance(inner, ast.Attribute) and inner.attr == "mark":
            base = inner.value
            if isinstance(base, ast.Name) and base.id == "pytest":
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
    for node in ast.walk(tree):
        if _is_pytest_skip_call(node):
            return node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for deco in node.decorator_list:
                for mark_name in ("skipif", "skip", "xfail"):
                    if _is_pytest_mark_decorator(deco, mark_name):
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
) -> list[tuple[str, str, str, int]]:
    """Walk every ``root/*.py`` file (except EXEMPT_FILES) and return every
    skip-style occurrence as ``(filename, qualname, kind, lineno)``.

    Pure function of ``root`` -- parameterized so self-tests can point it at
    a ``tmp_path`` fixture instead of the real tests/ directory, following
    ``tests/test_cli_helper_usage.py``'s ``_derive_test_files()`` discipline.
    ``lineno`` is retained only for human-readable failure messages; it does
    not participate in registry matching.
    """
    occurrences: list[tuple[str, str, str, int]] = []

    for py_file in sorted(root.rglob("*.py")):
        if py_file.name in EXEMPT_FILES:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, OSError):
            continue

        for node in ast.walk(tree):
            # 1. Direct calls: pytest.skip(...) / pytest.importorskip(...)
            if _is_pytest_skip_call(node):
                func = node.func
                attr = func.attr if isinstance(func, ast.Attribute) else "?"
                qualname = _enclosing_qualname(tree, node)
                occurrences.append((py_file.name, qualname, f"pytest.{attr}", node.lineno))

            # 2. Decorators on functions/classes: @pytest.mark.{skipif,skip,xfail}(...)
            decorators: list[ast.AST] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decorators = list(node.decorator_list)
            for deco in decorators:
                for mark_name in ("skipif", "skip", "xfail"):
                    if _is_pytest_mark_decorator(deco, mark_name):
                        qualname = _enclosing_qualname(tree, deco)
                        occurrences.append(
                            (py_file.name, qualname, f"@pytest.mark.{mark_name}", deco.lineno)
                        )

    return occurrences


@pytest.mark.skip_registry_gate
def test_no_unregistered_skips() -> None:
    """Every pytest skip-style marker in tests/ must be in ALLOWED_SKIPS,
    keyed by ``(file, qualname)`` per Phase 184 D-01."""
    violations = [
        occurrence
        for occurrence in _find_skip_occurrences()
        if not _allowed(occurrence[0], occurrence[1])
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
