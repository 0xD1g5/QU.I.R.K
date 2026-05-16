# PERMANENT INVARIANT — DO NOT REMOVE (v4.10-D-01 / CMVP-07)
#
# This test cannot be removed without explicit documented rationale in
# PROJECT.md Key Decisions referencing v4.10-D-01.
#
# The 'certified' tier is reserved indefinitely for a future CMVP attestation
# path. Algorithm-name matching alone is INSUFFICIENT to certify a module —
# certification requires the specific module + the specific environment +
# legal attestation. See .planning/phases/81-cmvp-attestation-feed/81-CONTEXT.md.
#
# Asserts: no code path under quirk/compliance/ or quirk/cbom/ emits
# ``certified: True`` via any of THREE syntactic patterns:
#   1. Dict literal: ``{"certified": True}``
#   2. Keyword call: ``f(certified=True)``
#   3. Subscript/attr assignment: ``d["certified"] = True`` or ``o.certified = True``
"""Phase 81 CMVP-07 / v4.10-D-01 PERMANENT INVARIANT.

DO NOT REMOVE without explicit documented rationale in PROJECT.md Key Decisions
referencing v4.10-D-01.
"""
from __future__ import annotations

import ast
import pathlib
import textwrap


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_KEY = "certified"
TARGET_DIRS = [
    PROJECT_ROOT / "quirk" / "compliance",
    PROJECT_ROOT / "quirk" / "cbom",
]


def _iter_py_files():
    for d in TARGET_DIRS:
        if d.exists():
            yield from d.rglob("*.py")


def _collect_violations(tree: ast.AST, src_path: pathlib.Path) -> list[str]:
    """Return human-readable violation strings for every offending node."""
    violations: list[str] = []
    for node in ast.walk(tree):
        # Pattern 1: dict literal {"certified": True}
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if (
                    isinstance(k, ast.Constant)
                    and k.value == FORBIDDEN_KEY
                    and isinstance(v, ast.Constant)
                    and v.value is True
                ):
                    line = getattr(k, "lineno", getattr(node, "lineno", -1))
                    violations.append(
                        f"{src_path}:{line}: dict literal 'certified': True"
                    )
        # Pattern 2: kwarg certified=True on any Call
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if (
                    kw.arg == FORBIDDEN_KEY
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    violations.append(
                        f"{src_path}:{node.lineno}: kwarg certified=True"
                    )
        # Pattern 3: subscript/attr assignment certified=True
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                is_subscript = (
                    isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.slice, ast.Constant)
                    and tgt.slice.value == FORBIDDEN_KEY
                )
                is_attr = (
                    isinstance(tgt, ast.Attribute)
                    and tgt.attr == FORBIDDEN_KEY
                )
                if (is_subscript or is_attr) and (
                    isinstance(node.value, ast.Constant)
                    and node.value.value is True
                ):
                    label = "subscript ['certified']" if is_subscript else "attribute .certified"
                    violations.append(
                        f"{src_path}:{node.lineno}: {label} = True"
                    )
    return violations


# ---------------------------------------------------------------------------
# Production assertion: every *.py under quirk/compliance/ and quirk/cbom/
# must pass clean — the permanent invariant.
# ---------------------------------------------------------------------------

def test_no_certified_true_in_cmvp_or_cbom() -> None:
    """v4.10-D-01 / CMVP-07 PERMANENT INVARIANT.

    No code path in quirk/compliance/ or quirk/cbom/ may emit
    ``certified: True`` via any of the three syntactic patterns above.
    """
    all_violations: list[str] = []
    files_scanned = 0
    for src in _iter_py_files():
        files_scanned += 1
        tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
        all_violations.extend(_collect_violations(tree, src))
    assert files_scanned > 0, (
        "AST gate could not find any quirk/compliance/*.py or "
        "quirk/cbom/*.py files — directory layout drifted."
    )
    assert not all_violations, (
        "v4.10-D-01 / CMVP-07 PERMANENT INVARIANT violated.\n"
        "Algorithm-name matching alone is INSUFFICIENT to claim CMVP "
        "certification — see .planning/phases/81-cmvp-attestation-feed/81-CONTEXT.md.\n"
        + "\n".join(all_violations)
    )


# ---------------------------------------------------------------------------
# Positive self-tests — each forbidden pattern MUST be caught.
# ---------------------------------------------------------------------------

def test_gate_catches_dict_literal_certified_true() -> None:
    """Pattern 1: ``{"certified": True}`` literal triggers the gate."""
    source = textwrap.dedent(
        """\
        payload = {"name": "AES", "certified": True}
        """
    )
    tree = ast.parse(source, filename="<synthetic-dict>")
    violations = _collect_violations(tree, pathlib.Path("<synthetic-dict>"))
    assert len(violations) == 1, f"expected 1 violation, got: {violations}"
    assert "dict literal" in violations[0]


def test_gate_catches_kwarg_certified_true() -> None:
    """Pattern 2: ``Property(certified=True)`` kwarg triggers the gate."""
    source = textwrap.dedent(
        """\
        def Property(**kw): pass
        Property(name="x", certified=True)
        """
    )
    tree = ast.parse(source, filename="<synthetic-kwarg>")
    violations = _collect_violations(tree, pathlib.Path("<synthetic-kwarg>"))
    assert len(violations) == 1, f"expected 1 violation, got: {violations}"
    assert "kwarg certified=True" in violations[0]


def test_gate_catches_subscript_assignment_certified_true() -> None:
    """Pattern 3a: ``d["certified"] = True`` subscript triggers the gate."""
    source = textwrap.dedent(
        """\
        d = {}
        d["certified"] = True
        """
    )
    tree = ast.parse(source, filename="<synthetic-subscript>")
    violations = _collect_violations(
        tree, pathlib.Path("<synthetic-subscript>")
    )
    assert len(violations) == 1, f"expected 1 violation, got: {violations}"
    assert "subscript ['certified']" in violations[0]


def test_gate_catches_attribute_assignment_certified_true() -> None:
    """Pattern 3b: ``obj.certified = True`` attribute triggers the gate."""
    source = textwrap.dedent(
        """\
        class _O: pass
        o = _O()
        o.certified = True
        """
    )
    tree = ast.parse(source, filename="<synthetic-attr>")
    violations = _collect_violations(tree, pathlib.Path("<synthetic-attr>"))
    assert len(violations) == 1, f"expected 1 violation, got: {violations}"
    assert "attribute .certified" in violations[0]


def test_gate_catches_all_three_patterns_combined() -> None:
    """A file mixing all three patterns reports exactly three violations."""
    source = textwrap.dedent(
        """\
        def Property(**kw): pass
        payload = {"certified": True}
        Property(certified=True)
        d = {}
        d["certified"] = True
        """
    )
    tree = ast.parse(source, filename="<synthetic-combo>")
    violations = _collect_violations(tree, pathlib.Path("<synthetic-combo>"))
    assert len(violations) == 3, (
        f"expected 3 violations (dict + kwarg + subscript), got: {violations}"
    )


# ---------------------------------------------------------------------------
# Negative self-tests — clean code must produce ZERO violations.
# ---------------------------------------------------------------------------

def test_gate_does_not_flag_unrelated_key() -> None:
    """``{"not_certified": True}`` and ``{"certified": False}`` are clean."""
    source = textwrap.dedent(
        """\
        a = {"not_certified": True}
        b = {"certified": False}
        c = {"certified_modules": ["OpenSSL FIPS Provider"]}
        """
    )
    tree = ast.parse(source, filename="<synthetic-clean>")
    violations = _collect_violations(tree, pathlib.Path("<synthetic-clean>"))
    assert violations == [], (
        f"Gate flagged clean code: {violations}"
    )


def test_gate_does_not_flag_informational_coverage_strings() -> None:
    """The legitimate ``fips_140_3_coverage`` / ``cmvp-coverage`` keys with
    informational string values must NOT be flagged."""
    source = textwrap.dedent(
        """\
        component_property = {
            "name": "quirk:cmvp-coverage",
            "value": "OpenSSL FIPS Provider, AWS-LC",
        }
        algo_record = {
            "name": "AES-256-GCM",
            "fips_140_3_coverage": ["OpenSSL FIPS Provider"],
        }
        """
    )
    tree = ast.parse(source, filename="<synthetic-informational>")
    violations = _collect_violations(
        tree, pathlib.Path("<synthetic-informational>")
    )
    assert violations == [], (
        f"Gate flagged informational coverage code: {violations}"
    )


# ---------------------------------------------------------------------------
# Meta-test: the permanent-invariant header must remain in this file.
# ---------------------------------------------------------------------------

def test_invariant_test_self_protection() -> None:
    """A future PR removing the permanent-invariant header should be caught.

    Tracks v4.10-D-01 + CMVP-07 + 'PERMANENT INVARIANT' marker presence so a
    grep CI gate or human review can flag stripped headers.
    """
    text = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert "v4.10-D-01" in text
    assert "CMVP-07" in text
    assert "PERMANENT INVARIANT" in text
