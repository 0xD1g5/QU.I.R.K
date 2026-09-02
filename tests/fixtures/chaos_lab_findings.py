"""Phase 49 D-04: source-of-truth aggregator for the title-join gate.

Serves two gates:

1. The compliance title-join gate (``tests/test_compliance_title_join.py``'s
   original two tests) — walks ``quirk/engine/findings_evaluator.py`` via
   ``ast`` and extracts every ``title=`` literal passed to
   ``_build_finding(...)``. Fixed-string titles are preserved verbatim
   (parens included). f-string titles are reduced to their literal-only
   template (constant parts joined; FormattedValue parts dropped) so
   ``TITLE_PREFIX_ALIASES`` can normalize them to the canonical
   COMPLIANCE_MAP key.

2. Phase 178 IDENT-01's identity-classification gate — walks
   ``quirk/dashboard/api/routes/scan.py`` (the second derivation path,
   which has no chokepoint function) for the same interpolated-title
   surface, and unions both files' f-string templates so
   ``quirk.compliance.TITLE_IDENTITY_CLASS`` can be checked for exact
   coverage: every interpolated title in EITHER path must be a classified
   key, closing the growing-set defect the gate exists to prevent.

Why AST over a runtime engine sweep: chaos lab requires Docker; CI must
not depend on it. AST extraction reads the literal title strings
deterministically from source — exactly the join surface the gate is
protecting.

Phase 72 D-05 / WR-10: file path was renamed risk_engine.py → findings_evaluator.py;
the 2-line shim at the old path no longer contains _build_finding call sites.

Phase 178 IDENT-01: this fixture's own ad-hoc `_normalize` reimplementation
(the third of three duplicate copies) has been collapsed into the single
public `quirk.compliance.normalize_finding_title`.
"""
from __future__ import annotations

import ast
import pathlib
from typing import Optional, Tuple

from quirk.compliance import normalize_finding_title

_RISK_ENGINE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "quirk/engine/findings_evaluator.py"
)

# Phase 178 IDENT-01: the second derivation path — no chokepoint function,
# titles passed directly as `title=` keywords to five finding-dataclass
# constructors across three `_derive_*_findings` functions.
_SCAN_ROUTES = (
    pathlib.Path(__file__).resolve().parents[2]
    / "quirk/dashboard/api/routes/scan.py"
)

_DASHBOARD_FINDING_CTORS = frozenset({
    "FindingItem",
    "IdentityFinding",
    "DarFinding",
    "MotionFinding",
    "HardwareFinding",
})


def _joined_str_literal(v: ast.JoinedStr) -> str:
    """Build the literal-only template from a JoinedStr: constants joined,
    FormattedValue (interpolated expression) parts dropped.

    Deliberately NOT `.strip()`'d — a leading/trailing space produced by a
    start- or end-interpolated f-string (e.g. `f"{proto} encryption
    posture"` -> `" encryption posture"`) is part of the identity of the
    template and is exactly what `TITLE_IDENTITY_CLASS`'s keys record.
    Stripping it here would make the guard's keys silently stop matching
    the classification table's keys.
    """
    return "".join(p.value for p in v.values if isinstance(p, ast.Constant))


def _template_from_keyword(kw: ast.keyword) -> Optional[Tuple[str, bool]]:
    """Extract `(template, is_fstring)` from a `title=` keyword's value, or
    `None` if the value is not a literal/f-string form this gate can read
    (e.g. `title=idf.title` — an attribute reference, not an interpolation
    site; correctly excluded).

    Handles three forms:
      - `ast.Constant` str -> `(value, False)`, preserved verbatim.
      - `ast.JoinedStr` -> `(literal-only template, True)`.
      - `ast.Call` on `.strip()`/`.lstrip()`/`.rstrip()` of an `ast.JoinedStr`
        or `ast.Constant` (e.g. `title=f"S3 bucket {bucket}".strip()`) ->
        recurse into the receiver so the `.strip()` wrapper doesn't hide
        the template from extraction. Do NOT actually strip the extracted
        string — the wrapped call is invoked at runtime, not applied to the
        AST-derived template (see the no-whitespace-strip rule above).
    """
    v = kw.value
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return (v.value, False)
    if isinstance(v, ast.JoinedStr):
        return (_joined_str_literal(v), True)
    if (
        isinstance(v, ast.Call)
        and isinstance(v.func, ast.Attribute)
        and v.func.attr in {"strip", "lstrip", "rstrip"}
    ):
        receiver = v.func.value
        if isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
            return (receiver.value, False)
        if isinstance(receiver, ast.JoinedStr):
            return (_joined_str_literal(receiver), True)
    return None


def collect_emitted_titles() -> set[str]:
    """Return the set of normalized finding titles emitted by
    findings_evaluator.py's `_build_finding` chokepoint.

    Behavior UNCHANGED from pre-refactor: same extraction outcomes, same
    normalization, same return value — only the per-keyword extraction now
    shares `_template_from_keyword` with `collect_dashboard_titles`.
    """
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
            result = _template_from_keyword(kw)
            if result is None:
                continue
            template, _is_fstring = result
            titles.add(normalize_finding_title(template))
    return titles


def collect_dashboard_titles() -> set[str]:
    """Return the set of RAW (un-normalized) literal-only templates passed
    as `title=` to any of the five finding-dataclass constructors in
    `quirk/dashboard/api/routes/scan.py` — the second derivation path,
    which has no chokepoint function.

    Returns exactly 12 templates, including the three extraction-gotcha
    cases: `"S3 bucket "` (the `.strip()` unwrap), `" encryption posture"`
    and `" cluster etcd encryption"` (start-interpolated, leading space
    preserved), and `"Quantum- algorithm: "` (mid-string interpolation).
    """
    tree = ast.parse(_SCAN_ROUTES.read_text())
    titles: set[str] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _DASHBOARD_FINDING_CTORS
        ):
            continue
        for kw in node.keywords:
            if kw.arg != "title":
                continue
            result = _template_from_keyword(kw)
            if result is None:
                continue
            template, is_fstring = result
            if is_fstring:
                titles.add(template)
    return titles


def collect_all_interpolated_templates() -> set[str]:
    """Return the union of f-string-derived (`is_fstring=True`) RAW
    templates from BOTH derivation paths, UN-normalized — these are the
    exact keys `quirk.compliance.TITLE_IDENTITY_CLASS` must cover.

    Length is exactly 22: 10 f-string sites in findings_evaluator.py plus
    the 12 in scan.py (`collect_dashboard_titles`).
    """
    templates: set[str] = set()

    tree = ast.parse(_RISK_ENGINE.read_text())
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
            result = _template_from_keyword(kw)
            if result is None:
                continue
            template, is_fstring = result
            if is_fstring:
                templates.add(template)

    templates |= collect_dashboard_titles()
    return templates
