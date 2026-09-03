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

Phase 180 (Plan 07) extended this guard to cover the closure computation
(`quirk/intelligence/closure.py`) and the burndown aggregation
(`quirk/intelligence/burndown.py`) — the largest advisory surface this
milestone built. ADVISORY-01 remains STANDING; it does NOT close in this
plan either. Per D-39, the `checked >=` floor MUST rise every time
`_GUARDED_MODULES` grows — a floor left stale while the tuple grows lets
modules be deleted, renamed, or moved without a single test failing, since
the `path.exists()` skip that keeps this guard wave-order independent is
precisely what makes a stale floor dangerous.

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
    # Phase 179 Plan 04's module — already landed, guarded since that phase.
    _QUIRK_INTELLIGENCE / "scope_signature.py",
    # Phase 180 Plan 04 (CLOSE-01) — the two-sided closure computation.
    _QUIRK_INTELLIGENCE / "closure.py",
    # Phase 180 Plan 06 (CLOSE-03) — per-deadline burndown aggregation.
    _QUIRK_INTELLIGENCE / "burndown.py",
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
            # A not-yet-landed module (wave-order independence) — skip
            # gracefully. test_guarded_modules_all_exist catches a module
            # that is STILL missing once the phase has landed.
            continue
        checked += 1
        source = path.read_text()
        assert not _imports_forbidden_module(source), (
            f"{path} imports the quantum-readiness weighting module — "
            "ADVISORY-01 violated"
        )
    # D-39: the floor rises with _GUARDED_MODULES. All five of
    # remediation.py, remediation_persist.py, scope_signature.py,
    # closure.py, and burndown.py exist as of this plan; a checked count
    # below 5 means one of them was silently skipped.
    assert checked >= 5, (
        "expected all 5 guarded modules to be checked "
        "(remediation.py, remediation_persist.py, scope_signature.py, "
        f"closure.py, burndown.py) but only checked={checked}"
    )


def test_guarded_modules_all_exist() -> None:
    """Companion to the `path.exists(): continue` skip above: that skip keeps
    the guard wave-order independent DURING a phase, but once a phase has
    landed, a permanently-missing guarded module must fail loudly rather
    than silently reduce `checked` below the floor.
    """
    missing = [str(p) for p in _GUARDED_MODULES if not p.exists()]
    assert missing == [], f"guarded module(s) missing on disk: {missing}"


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
    execution of Phase 179 Plan 03: a temporary `import
    quirk.intelligence.scoring` line was added to
    `quirk/intelligence/remediation_persist.py`,
    `test_remediation_modules_never_import_scoring` was observed to fail RED
    with the exact assertion message above, and the line was then reverted
    (`git status --short` confirmed clean). See 179-03-SUMMARY.md for the
    recorded RED output.

    The protocol was RE-RUN in Phase 180 Plan 07, this time against BOTH
    newly-guarded modules separately: a temporary `import
    quirk.intelligence.scoring` line was added to
    `quirk/intelligence/closure.py`, observed RED naming that module, and
    reverted; then the same was repeated for
    `quirk/intelligence/burndown.py`. Both verbatim RED outputs and the
    before/after `git status --short` captures are recorded in
    180-07-SUMMARY.md. One injection proving one module is not proof for
    the other — the walk is pointed at the module named in the failure
    message, not merely present in the tuple.
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
