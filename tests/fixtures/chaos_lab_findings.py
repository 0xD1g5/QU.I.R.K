"""Phase 49 D-04: source-of-truth aggregator for the title-join gate.

Walks ``quirk/engine/findings_evaluator.py`` via ``ast`` and extracts every
``title=`` literal passed to ``_build_finding(...)``. Fixed-string titles
are preserved verbatim (parens included). f-string titles are reduced to
their literal-only template (constant parts joined; FormattedValue parts
dropped) so ``TITLE_PREFIX_ALIASES`` can normalize them to the canonical
COMPLIANCE_MAP key.

Why AST over a runtime engine sweep: chaos lab requires Docker; CI must
not depend on it. AST extraction reads the literal title strings
deterministically from source — exactly the join surface the gate is
protecting.

Phase 72 D-05 / WR-10: file path was renamed risk_engine.py → findings_evaluator.py;
the 2-line shim at the old path no longer contains _build_finding call sites.
"""
from __future__ import annotations

import ast
import pathlib

_RISK_ENGINE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "quirk/engine/findings_evaluator.py"
)


def _normalize(title: str) -> str:
    """Apply the SAME normalization quirk.engine.risk_engine._normalize_for_compliance
    applies at runtime. Lazy-imports TITLE_PREFIX_ALIASES so this fixture is
    collectable before quirk.compliance exists (RED state)."""
    try:
        from quirk.compliance import TITLE_PREFIX_ALIASES
    except ImportError:
        TITLE_PREFIX_ALIASES = {}
    # Longest-prefix-first so "Severely outdated Python cryptography package ("
    # wins over any shorter overlapping prefix.
    for prefix in sorted(TITLE_PREFIX_ALIASES, key=len, reverse=True):
        if title.startswith(prefix):
            return TITLE_PREFIX_ALIASES[prefix]
    return title


def collect_emitted_titles() -> set[str]:
    """Return the set of normalized finding titles emitted by risk_engine.py."""
    tree = ast.parse(_RISK_ENGINE.read_text())
    titles: set[str] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_build_finding"
        ):
            continue
        for kw in node.keywords:
            if kw.arg != "title":
                continue
            v = kw.value
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                # Fixed-string title — preserve verbatim (incl. trailing parens).
                titles.add(_normalize(v.value))
            elif isinstance(v, ast.JoinedStr):
                # f-string: build literal-only template (constants joined,
                # FormattedValue parts dropped). The result is exactly the
                # prefix that TITLE_PREFIX_ALIASES is keyed on (up through
                # the first " (" or analogous interpolation marker).
                lit = "".join(
                    p.value for p in v.values if isinstance(p, ast.Constant)
                )
                titles.add(_normalize(lit))
    return titles
