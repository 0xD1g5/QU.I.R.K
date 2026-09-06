"""Phase 41 D-03: CI gate meta-test that fails when an unregistered
``pytest.skip`` / ``pytest.importorskip`` / ``@pytest.mark.skipif`` /
``@pytest.mark.skip`` / ``@pytest.mark.xfail``
is encountered in tests/.

Mechanism: walk every ``tests/*.py`` file with ``ast.parse`` + ``ast.walk``
looking for:
  - Call nodes whose func resolves to ``pytest.skip`` or ``pytest.importorskip``
  - Decorator nodes whose func resolves to ``pytest.mark.skipif``,
    ``pytest.mark.skip``, or ``pytest.mark.xfail``

For each occurrence, check ``(filename, node.lineno)`` against
``tests.skip_registry.ALLOWED_SKIPS`` with a +/-2 line tolerance to absorb
minor edits. Any unregistered occurrence is a violation.

NOTE: At creation time (Wave 0 of Phase 41) some D-04 deletions have NOT yet
happened, so this test will FAIL initially. That is correct — Plan 05 deletes
the stale skips identified in 41-RESEARCH.md and turns this gate green.

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
LINE_TOLERANCE = 2

# Files exempt from the walk: the registry itself and this gate test.
EXEMPT_FILES = {"skip_registry.py", "test_skip_registry.py"}


def _allowed(filename: str, lineno: int) -> bool:
    """Return True iff (filename, lineno) is in ALLOWED_SKIPS within +/-LINE_TOLERANCE."""
    for entry_file, entry_line, _category, _reason in ALLOWED_SKIPS:
        if entry_file == filename and abs(entry_line - lineno) <= LINE_TOLERANCE:
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


@pytest.mark.skip_registry_gate
def test_no_unregistered_skips() -> None:
    """Every pytest skip-style marker in tests/ must be in ALLOWED_SKIPS.

    Initial Wave 0 state: this test FAILS until Plan 05 deletes the stale
    skips listed in 41-RESEARCH.md "Skip-Marker Triage Table" (D-04).
    """
    violations: list[tuple[str, int, str]] = []

    for py_file in sorted(TESTS_DIR.rglob("*.py")):
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
                if not _allowed(py_file.name, node.lineno):
                    func = node.func
                    attr = func.attr if isinstance(func, ast.Attribute) else "?"
                    violations.append((py_file.name, node.lineno, f"pytest.{attr}"))

            # 2. Decorators on functions/classes: @pytest.mark.{skipif,skip,xfail}(...)
            decorators: list[ast.AST] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decorators = list(node.decorator_list)
            for deco in decorators:
                for mark_name in ("skipif", "skip", "xfail"):
                    if _is_pytest_mark_decorator(deco, mark_name):
                        if not _allowed(py_file.name, deco.lineno):
                            violations.append(
                                (py_file.name, deco.lineno, f"@pytest.mark.{mark_name}")
                            )

    if violations:
        formatted = "\n".join(
            f"  {fname}:{lineno} [{kind}]" for fname, lineno, kind in violations
        )
        pytest.fail(
            "Unregistered skip markers found (add to tests/skip_registry.py "
            "ALLOWED_SKIPS or delete the marker per Phase 41 D-01/D-04):\n"
            f"{formatted}"
        )
