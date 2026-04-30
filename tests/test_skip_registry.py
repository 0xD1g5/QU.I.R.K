"""Phase 41 D-03: CI gate meta-test that fails when an unregistered
``pytest.skip`` / ``pytest.importorskip`` / ``@pytest.mark.skipif``
is encountered in tests/.

Mechanism: walk every ``tests/*.py`` file with ``ast.parse`` + ``ast.walk``
looking for:
  - Call nodes whose func resolves to ``pytest.skip`` or ``pytest.importorskip``
  - Decorator nodes whose func resolves to ``pytest.mark.skipif``

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


def _is_pytest_skipif_decorator(node: ast.AST) -> bool:
    """True if ``node`` is ``@pytest.mark.skipif(...)`` decorator."""
    # Decorator can be either a Call (with args) or a plain Attribute access.
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and target.attr == "skipif":
        # target.value should be ast.Attribute pytest.mark
        inner = target.value
        if isinstance(inner, ast.Attribute) and inner.attr == "mark":
            base = inner.value
            if isinstance(base, ast.Name) and base.id == "pytest":
                return True
    return False


@pytest.mark.skip_registry_gate
def test_no_unregistered_skips() -> None:
    """Every pytest skip-style marker in tests/ must be in ALLOWED_SKIPS.

    Initial Wave 0 state: this test FAILS until Plan 05 deletes the stale
    skips listed in 41-RESEARCH.md "Skip-Marker Triage Table" (D-04).
    """
    violations: list[tuple[str, int, str]] = []

    for py_file in sorted(TESTS_DIR.glob("*.py")):
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

            # 2. Decorators on functions/classes: @pytest.mark.skipif(...)
            decorators: list[ast.AST] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decorators = list(node.decorator_list)
            for deco in decorators:
                if _is_pytest_skipif_decorator(deco):
                    if not _allowed(py_file.name, deco.lineno):
                        violations.append(
                            (py_file.name, deco.lineno, "@pytest.mark.skipif")
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
