"""Phase 77-03 D-19 (api-cli-core/IN-04): QRAMM multiplier magic numbers
extracted to named constants.

RESEARCH C-2 / Pitfall 2: the magic numbers `0.8 / 1.5 / 0.10 / 0.20` live in
`quirk/dashboard/api/routes/qramm.py` (NOT `quirk/qramm/scoring.py` as CONTEXT
D-19 claimed). The Phase 75 D-06 band [0.8, 1.5] is enforced here.
"""
from __future__ import annotations

import ast
import pathlib


_QRAMM_PATH = pathlib.Path("quirk/dashboard/api/routes/qramm.py")
_TARGET_VALUES = {0.8, 1.5, 0.10, 0.20}


def test_multiplier_constants_defined() -> None:
    """D-19: module-level constants must exist with the canonical values."""
    from quirk.dashboard.api.routes.qramm import (  # noqa: WPS433
        MULTIPLIER_HIGH_STEP,
        MULTIPLIER_LOW_STEP,
        MULTIPLIER_MAX,
        MULTIPLIER_MIN,
    )

    assert MULTIPLIER_MIN == 0.8
    assert MULTIPLIER_MAX == 1.5
    assert MULTIPLIER_LOW_STEP == 0.10
    assert MULTIPLIER_HIGH_STEP == 0.20


def _named_constant_lineno(tree: ast.AST, name: str) -> int | None:
    """Return the line number of a module-level constant assignment, or None."""
    for node in tree.body:  # type: ignore[attr-defined]
        # Match both `MULTIPLIER_MIN = 0.8` and `MULTIPLIER_MIN: float = 0.8`.
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                return node.lineno
    return None


def test_no_remaining_literal_multiplier_numbers() -> None:
    """D-19: count `Constant` float nodes equal to 0.8/1.5/0.10/0.20 across the
    module. Only the 4 constant-definition assignments are allowed."""
    src = _QRAMM_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)

    allowed_linenos = {
        _named_constant_lineno(tree, n)
        for n in ("MULTIPLIER_MIN", "MULTIPLIER_MAX", "MULTIPLIER_LOW_STEP", "MULTIPLIER_HIGH_STEP")
    }
    assert None not in allowed_linenos, (
        "D-19: all 4 MULTIPLIER_* module-level constants must be defined"
    )

    offenders: list[tuple[int, float]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            if node.value in _TARGET_VALUES and node.lineno not in allowed_linenos:
                offenders.append((node.lineno, node.value))

    assert not offenders, (
        "D-19: stray multiplier literals remain (line, value): "
        + ", ".join(f"L{ln}={v}" for ln, v in offenders)
    )
