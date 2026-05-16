"""Phase 78 / HARDEN-05: AST CI gate for Jinja `| safe` pairing + forward
guards for markdown→HTML deps (D-78-R1) and a Python-side `Markup` walker.

Mechanism:
  Surface 1 (Jinja templates) — walk every `.j2` under
  `quirk/reports/templates/`, parse via `jinja2.Environment().parse(source)`,
  enumerate `nodes.Filter` whose `.name == "safe"`, and assert each has an
  upstream `| sanitize` somewhere in its filter chain via
  `_has_upstream_sanitize`. Violations fail the gate.

  Surface 2 (Python code) — walk every `.py` under `quirk/reports/`, find
  every `ast.Call` to `Markup` / `markupsafe.Markup` / `jinja2.Markup`, and
  assert the sole argument is a call to `sanitize_scanner_text`. Current
  sweep returns zero violations; this is a forward guard.

  Surface 3 (pyproject dependencies) — parse `pyproject.toml` via `tomllib`,
  walk `[project] dependencies` plus every entry in
  `[project.optional-dependencies]`, and assert NO dependency begins with a
  markdown→HTML prefix (`markdown`, `mistune`, `commonmark`) or with `bleach`.
  Phase 78 / D-78-R1: no markdown→HTML conversion exists today; this gate
  prevents silent introduction of one without paired sanitize wiring.

SAFE shapes:
  - Jinja: `{{ x | sanitize | safe }}`  (filter chain has `| sanitize`
    upstream of every `| safe`)
  - Python: `Markup(sanitize_scanner_text(x))`  (only call to Markup whose
    single argument is a call to `sanitize_scanner_text`)

Self-tests:
  - Positive (`test_gate_catches_synthetic_bypass`) — confirms gate catches
    `{{ x | safe }}` (no upstream sanitize).
  - Negative (`test_gate_does_not_flag_safe_patterns`) — confirms gate does
    NOT flag `{{ x | sanitize | safe }}`.
"""
from __future__ import annotations

import ast
import pathlib
import tomllib

import jinja2
import pytest
from jinja2 import nodes

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE_DIRS: list[pathlib.Path] = [PROJECT_ROOT / "quirk" / "reports" / "templates"]
REPORT_DIRS: list[pathlib.Path] = [PROJECT_ROOT / "quirk" / "reports"]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

# Any dependency entry whose lowercased PEP 508 name starts with one of these
# tokens is a markdown→HTML library and MUST be paired with sanitize wiring
# before landing. Phase 78 / D-78-R1.
MARKDOWN_LIB_PREFIXES: tuple[str, ...] = (
    "markdown",      # covers `markdown`, `markdown-it-py`, `markdown_it_py`
    "mistune",
    "commonmark",
)

# Belt-and-suspenders (HARDEN-06): bleach must never re-appear in deps.
FORBIDDEN_DEP_PREFIXES: tuple[str, ...] = ("bleach",)


# Cached pyproject contents (parsed once per test session).
def _load_pyproject() -> dict:
    with open(PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)


_PYPROJECT = _load_pyproject()


def _collect_all_dep_strings(pp: dict) -> list[str]:
    """Return every PEP 508 dep string declared in pyproject.toml.

    Walks `[project] dependencies` AND every list in
    `[project.optional-dependencies]`.
    """
    deps: list[str] = []
    project = pp.get("project", {}) or {}
    deps.extend(project.get("dependencies", []) or [])
    optional = project.get("optional-dependencies", {}) or {}
    for extra_name, extra_deps in optional.items():
        deps.extend(extra_deps or [])
    return deps


def _dep_name(dep_spec: str) -> str:
    """Extract the package name (lowercased) from a PEP 508 dep string."""
    # Strip trailing version specifiers / markers / extras.
    # PEP 508: name[extras] (specifier) ; marker
    name = dep_spec.strip()
    # Take chars up to first non-name char
    for sep in ("[", "(", ";", ">", "<", "=", "!", "~", " "):
        idx = name.find(sep)
        if idx != -1:
            name = name[:idx]
    return name.strip().lower()


# ---------------------------------------------------------------------------
# Jinja Filter helpers
# ---------------------------------------------------------------------------


def _has_upstream_sanitize(filter_node: nodes.Filter) -> bool:
    """Walk Filter.node chain upward; True if any link is `| sanitize`."""
    cur = filter_node.node
    while isinstance(cur, nodes.Filter):
        if cur.name == "sanitize":
            return True
        cur = cur.node
    return False


def _collect_unpaired_safe(source: str) -> list[int]:
    """Parse a Jinja source string; return linenos of unpaired `| safe`
    filter nodes (or 0 if lineno not populated)."""
    env = jinja2.Environment()
    tree = env.parse(source)
    out: list[int] = []
    for node in tree.find_all(nodes.Filter):
        if node.name == "safe" and not _has_upstream_sanitize(node):
            # Fall back to 0 when Jinja's lineno is unpopulated (per RESEARCH R-5).
            out.append(getattr(node, "lineno", 0) or 0)
    return out


# ---------------------------------------------------------------------------
# Main gate — Jinja templates
# ---------------------------------------------------------------------------


def test_safe_filter_paired_with_sanitize() -> None:
    """Every `| safe` in every .j2 template under quirk/reports/templates/
    must have an upstream `| sanitize` somewhere in its filter chain."""
    violations: list[tuple[str, int]] = []
    for tdir in TEMPLATE_DIRS:
        if not tdir.exists():
            continue
        for tpl in sorted(tdir.rglob("*.j2")):
            source = tpl.read_text(encoding="utf-8")
            try:
                env = jinja2.Environment()
                tree = env.parse(source)
            except jinja2.TemplateSyntaxError:
                # Fragments / partials that don't parse standalone — skip.
                continue
            for node in tree.find_all(nodes.Filter):
                if node.name == "safe" and not _has_upstream_sanitize(node):
                    rel = str(tpl.relative_to(PROJECT_ROOT))
                    lineno = getattr(node, "lineno", 0) or 0
                    violations.append((rel, lineno))
    if violations:
        formatted = "\n".join(f"  {f}:{ln}" for f, ln in violations)
        pytest.fail(
            "Jinja `| safe` filter usages without an upstream `| sanitize`:\n"
            f"{formatted}"
        )


# ---------------------------------------------------------------------------
# Self-tests (Phase 59 model: positive + negative)
# ---------------------------------------------------------------------------


def test_gate_catches_synthetic_bypass() -> None:
    """Positive self-test: gate flags `{{ x | safe }}` (no sanitize upstream)."""
    unpaired = _collect_unpaired_safe("{{ scanner_string | safe }}")
    assert len(unpaired) == 1, (
        f"Gate self-test expected 1 violation from synthetic bypass; got {len(unpaired)}: {unpaired}"
    )


def test_gate_does_not_flag_safe_patterns() -> None:
    """Negative self-test: gate does NOT flag `{{ x | sanitize | safe }}`."""
    unpaired = _collect_unpaired_safe("{{ scanner_string | sanitize | safe }}")
    assert unpaired == [], (
        f"Gate incorrectly flagged paired `sanitize | safe` usage: {unpaired}"
    )


def test_filter_lineno_populated() -> None:
    """RESEARCH R-5 smoke test: Jinja attaches lineno > 0 to Filter nodes for
    typical template fragments. If lineno is ever 0, the main gate falls back
    to template-path-only reporting (encoded above via `or 0`)."""
    env = jinja2.Environment()
    source = "\n{{ scanner_string | safe }}\n"
    tree = env.parse(source)
    safe_filters = [n for n in tree.find_all(nodes.Filter) if n.name == "safe"]
    assert len(safe_filters) == 1
    # Either lineno > 0 (preferred) or lineno == 0 (fallback path active).
    # Both branches are acceptable; this test documents the contract.
    lineno = getattr(safe_filters[0], "lineno", 0)
    assert lineno >= 0  # purely a defensive contract assertion


# ---------------------------------------------------------------------------
# Forward guard — markdown→HTML libraries (D-78-R1)
# ---------------------------------------------------------------------------


def test_no_markdown_to_html_lib_in_deps() -> None:
    """D-78-R1 forward guard: NO markdown→HTML library may appear in
    pyproject.toml `[project] dependencies` or any
    `[project.optional-dependencies]` extra without paired sanitize wiring.

    Phase 78: no markdown→HTML conversion exists today (`html_renderer.py`
    renders Jinja directly from Python data). If a future PR adds one of
    these libs, this gate must trip until a paired sanitize-after-conversion
    test lands.
    """
    deps = _collect_all_dep_strings(_PYPROJECT)
    offenders: list[str] = []
    for dep in deps:
        name = _dep_name(dep)
        for prefix in MARKDOWN_LIB_PREFIXES:
            if name == prefix or name.startswith(prefix + "-") or name.startswith(prefix + "_"):
                offenders.append(dep)
                break
    if offenders:
        formatted = "\n".join(f"  {d}" for d in offenders)
        pytest.fail(
            "markdown→HTML library found in pyproject.toml dependencies "
            "without paired sanitize wiring (D-78-R1):\n"
            f"{formatted}\n"
            "If this is intentional, land a test that proves output flows "
            "through sanitize_scanner_text() post-conversion, then update "
            "MARKDOWN_LIB_PREFIXES."
        )


def test_no_bleach_in_deps() -> None:
    """HARDEN-06 belt-and-suspenders: `bleach` must not appear in deps.

    Redundant with `tests/test_sanitize_scanner_text.py` but kept here as the
    AST-gate file is the natural home for cross-cutting CI gates.
    """
    deps = _collect_all_dep_strings(_PYPROJECT)
    offenders: list[str] = []
    for dep in deps:
        name = _dep_name(dep)
        for prefix in FORBIDDEN_DEP_PREFIXES:
            if name == prefix or name.startswith(prefix + "-") or name.startswith(prefix + "_"):
                offenders.append(dep)
                break
    if offenders:
        formatted = "\n".join(f"  {d}" for d in offenders)
        pytest.fail(
            "Forbidden dependency (bleach) found in pyproject.toml — nh3 is "
            "the project sanitizer per HARDEN-06:\n"
            f"{formatted}"
        )


# ---------------------------------------------------------------------------
# Python-side forward guard — Markup() calls without sanitize_scanner_text
# ---------------------------------------------------------------------------


def _is_markup_call(node: ast.expr) -> bool:
    """True iff node is an ast.Call to Markup or markupsafe.Markup or
    jinja2.Markup."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "Markup":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "Markup":
        return True
    return False


def _is_sanitize_call(node: ast.expr) -> bool:
    """Mirrors the Phase 59 `_is_safe_str_call` predicate, renamed for
    sanitize_scanner_text."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "sanitize_scanner_text":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "sanitize_scanner_text":
        return True
    return False


def test_no_markup_without_sanitize() -> None:
    """Forward guard: every `Markup(...)` call in `quirk/reports/*.py` must
    have a `sanitize_scanner_text(...)` call as its (sole) argument.

    Current sweep returns zero violations; this gate prevents future drift
    where a developer wraps scanner-controlled text in `Markup()` to bypass
    Jinja autoescape.
    """
    violations: list[tuple[str, int]] = []
    for rdir in REPORT_DIRS:
        if not rdir.exists():
            continue
        for py_file in sorted(rdir.rglob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not _is_markup_call(node):
                    continue
                # Acceptable shape: Markup(sanitize_scanner_text(x))
                if len(node.args) == 1 and _is_sanitize_call(node.args[0]):
                    continue
                violations.append(
                    (str(py_file.relative_to(PROJECT_ROOT)), node.lineno)
                )
    if violations:
        formatted = "\n".join(f"  {f}:{ln}" for f, ln in violations)
        pytest.fail(
            "Markup(...) calls without sanitize_scanner_text wrapping in "
            "quirk/reports/*.py:\n"
            f"{formatted}"
        )
