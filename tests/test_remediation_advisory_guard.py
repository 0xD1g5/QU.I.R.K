"""Phase 179 (ADVISORY-01) — permanent, falsifiable regression guard: the
remediation modules must never import, call, or transit
``quirk.intelligence.scoring``, and the quantum-readiness score weights must
never contain a remediation/closure-derived key.

Phase 179's entire surface (three tables, one config section, a slug map, a
scan-time writer) has ZERO contact with the quantum-readiness score.
ADVISORY-01 ("remediation/closure state is advisory-only and never feeds the
quantum-readiness score") is a STANDING requirement across Phases 177-181 —
it does NOT close in this phase, and this guard must stay green forever,
through 180 (closure computation) and 181 (surfacing) as well.

This mirrors ``tests/test_cve_score_guard.py``'s existing machine-enforced
advisory-only firewall, applied to the remediation surface instead of the
hardware/CVE surface, in a SEPARATE file — ``test_cve_score_guard.py`` is
left byte-unchanged so its green result stays an independent signal and
``tests/skip_registry.py``'s (file, LINENO) allowances are not disturbed.

Phase 177 and 178 both proved that a guard nobody has watched fail is a
guard nobody knows works — the negative control below is not optional
decoration, it is the point: it runs the SAME AST walk against a fixture
source string that DOES import the scoring module, and asserts the walk
finds it. A guard that can only ever pass is not a guard.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_QUIRK_INTELLIGENCE = _REPO_ROOT / "quirk" / "intelligence"

_GUARDED_MODULES = (
    _QUIRK_INTELLIGENCE / "remediation.py",
    _QUIRK_INTELLIGENCE / "remediation_persist.py",
    # Plan 04 adds this module; guard it too once it exists so this test is
    # wave-order independent and nobody has to remember to extend the guard.
    _QUIRK_INTELLIGENCE / "scope_signature.py",
)

_FORBIDDEN_MODULE_NAMES = frozenset({"quirk.intelligence.scoring", "scoring"})

_FORBIDDEN_SCORE_KEY_SUBSTRINGS = ("remediation", "closure", "not_observed", "burndown")


def _imports_forbidden_module(source: str) -> bool:
    """AST-walk `source`, return True iff it imports a forbidden module name.

    Deliberately does NOT use substring/grep matching on the source text —
    an AST walk only flags genuine `import`/`from ... import` statements, so
    a comment or docstring mentioning the module name (as this very file's
    own docstring does, in prose) can never produce a false positive.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _FORBIDDEN_MODULE_NAMES:
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in _FORBIDDEN_MODULE_NAMES:
                return True
            for alias in node.names:
                if alias.name in _FORBIDDEN_MODULE_NAMES:
                    return True
    return False


def test_remediation_modules_never_import_scoring() -> None:
    checked = 0
    for path in _GUARDED_MODULES:
        if not path.exists():
            # Plan 04 has not landed yet (or landed under a different name) —
            # skip gracefully, wave-order independent.
            continue
        checked += 1
        source = path.read_text()
        assert not _imports_forbidden_module(source), (
            f"{path} imports the quantum-readiness weighting module — "
            "ADVISORY-01 violated"
        )
    # remediation.py and remediation_persist.py both exist as of this plan;
    # a checked count of zero would mean the guard silently checked nothing.
    assert checked >= 2


def test_score_weights_has_no_remediation_derived_key() -> None:
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [
        k for k in SCORE_WEIGHTS
        if any(term in k.lower() for term in _FORBIDDEN_SCORE_KEY_SUBSTRINGS)
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain remediation/closure-derived keys "
        f"(ADVISORY-01): {bad_keys}"
    )


def test_negative_control_ast_walk_detects_a_real_forbidden_import() -> None:
    """Prove the guard CAN fail: apply the same AST walk to a fixture source
    string that DOES import the forbidden module, two different ways, and
    assert detection.

    This is the mandatory negative control. It was run for real during
    execution of this plan: a temporary `import quirk.intelligence.scoring`
    line was added to `quirk/intelligence/remediation_persist.py`,
    `test_remediation_modules_never_import_scoring` was observed to fail RED
    with the exact assertion message above, and the line was then reverted
    (`git status --short` confirmed clean). See 179-03-SUMMARY.md for the
    recorded RED output.
    """
    fixture_plain_import = (
        "from __future__ import annotations\n"
        "import quirk.intelligence.scoring\n"
        "\n"
        "def foo():\n"
        "    return quirk.intelligence.scoring.SCORE_WEIGHTS\n"
    )
    assert _imports_forbidden_module(fixture_plain_import) is True

    fixture_from_import = (
        "from __future__ import annotations\n"
        "from quirk.intelligence import scoring\n"
        "\n"
        "def bar():\n"
        "    return scoring.SCORE_WEIGHTS\n"
    )
    assert _imports_forbidden_module(fixture_from_import) is True

    fixture_clean = (
        "from __future__ import annotations\n"
        "# this comment mentions quirk.intelligence.scoring in prose only\n"
        "def baz():\n"
        "    return 1\n"
    )
    assert _imports_forbidden_module(fixture_clean) is False
