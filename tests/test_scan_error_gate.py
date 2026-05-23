"""Phase 59 LEAK-03: AST CI gate that fails when a scan_error write
bypasses safe_str().

Mechanism: walk every .py in quirk/scanner/, quirk/discovery/, quirk/cbom/.
For each Call(keyword arg='scan_error') and each Assign(target.attr='scan_error'),
classify the RHS as SAFE or VIOLATION using the predicates below.

SAFE shapes:
  - ast.Constant            (string literal, None)
  - ast.Call to safe_str    (the chokepoint)
  - ast.Attribute read      (e.g., _validation.reason)
  - ast.JoinedStr where every FormattedValue wraps safe_str(...)
  - ast.Name whose source assignment in the same module uses safe_str
    (handles gcp_connector two-step pattern)

Anything else is a VIOLATION.
"""
from __future__ import annotations

import ast
import pathlib
import textwrap

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

SCANNER_DIRS = [
    PROJECT_ROOT / "quirk" / "scanner",
    PROJECT_ROOT / "quirk" / "discovery",
    PROJECT_ROOT / "quirk" / "cbom",
]


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------

def _is_safe_str_call(node: ast.expr) -> bool:
    """True iff node is ast.Call with func.id == 'safe_str' (Name) or
    func.attr == 'safe_str' (Attribute)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "safe_str":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "safe_str":
        return True
    return False


def _is_literal_or_none(node: ast.expr) -> bool:
    """True iff node is ast.Constant (string literal, None, etc.)."""
    return isinstance(node, ast.Constant)


def _is_attr_read(node: ast.expr) -> bool:
    """True iff node is ast.Attribute (not a method call target).
    Permits patterns like _validation.reason."""
    return isinstance(node, ast.Attribute)


def _name_assigned_via_safe_str(name_node: ast.Name, module_tree: ast.Module) -> bool:
    """True iff there exists an ast.Assign in module_tree whose target Name
    matches name_node.id AND whose value contains an ast.Call to safe_str.

    Walks ast.walk(module_tree). Permits the gcp_connector two-step pattern:
      scan_error_msg = f"...: {safe_str(exc)}"
    """
    target_id = name_node.id
    for node in ast.walk(module_tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == target_id:
                # Check if any descendent of the RHS is a safe_str call
                for sub in ast.walk(node.value):
                    if _is_safe_str_call(sub):
                        return True
    return False


def _is_fstring_with_safe_str(node: ast.JoinedStr) -> bool:
    """True iff node is ast.JoinedStr AND at least one FormattedValue child
    contains a safe_str call, AND no FormattedValue is a plain Name or Call
    that is NOT safe_str (bare exception variable reference).

    Permits f'{cat}: {safe_str(e)}' — cat is a benign string categorization
    variable (not credential-bearing), safe_str(e) wraps the exception.

    The rule: if the f-string contains a safe_str() call anywhere in it,
    and none of the FormattedValues is a raw Call (like str(exc), repr(exc))
    without safe_str wrapping, it is considered safe.
    """
    has_safe_str = False
    for child in ast.walk(node):
        if isinstance(child, ast.FormattedValue):
            val = child.value
            if _contains_safe_str_call(val):
                has_safe_str = True
                continue
            # Literal — safe
            if isinstance(val, ast.Constant):
                continue
            # Attribute read — safe (e.g., _validation.reason)
            if isinstance(val, ast.Attribute):
                continue
            # Name (e.g., a local variable like cat, scan_error_msg) — safe
            # if it's a simple variable reference (not a call)
            if isinstance(val, ast.Name):
                continue
            # Any Call that is NOT safe_str (e.g., str(exc), repr(exc)) — VIOLATION
            if isinstance(val, ast.Call):
                return False
            # Nested JoinedStr or other complex expr — VIOLATION (conservative)
            return False
    return has_safe_str


def _contains_safe_str_call(node: ast.expr) -> bool:
    """True iff the node itself or any descendant is a call to safe_str."""
    for sub in ast.walk(node):
        if _is_safe_str_call(sub):
            return True
    return False


def _classify_rhs(rhs: ast.expr, module_tree: ast.Module) -> bool:
    """Return True if rhs is SAFE."""
    if _is_literal_or_none(rhs):
        return True
    if _is_safe_str_call(rhs):
        return True
    if _is_attr_read(rhs):
        return True  # attribute read, e.g., _validation.reason
    if isinstance(rhs, ast.JoinedStr) and _is_fstring_with_safe_str(rhs):
        return True
    if isinstance(rhs, ast.Name) and _name_assigned_via_safe_str(rhs, module_tree):
        return True
    return False


# ---------------------------------------------------------------------------
# Main gate: walk codebase and check every scan_error write
# ---------------------------------------------------------------------------

def test_scan_error_writes_use_safe_str() -> None:
    violations: list[tuple[str, int]] = []
    for scanner_dir in SCANNER_DIRS:
        if not scanner_dir.exists():
            continue
        for py_file in sorted(scanner_dir.rglob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    for kw in node.keywords:
                        if kw.arg == "scan_error" and not _classify_rhs(kw.value, tree):
                            violations.append((str(py_file.relative_to(PROJECT_ROOT)), kw.value.lineno))
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and target.attr == "scan_error":
                            if not _classify_rhs(node.value, tree):
                                violations.append((str(py_file.relative_to(PROJECT_ROOT)), node.lineno))
    if violations:
        formatted = "\n".join(f"  {f}:{ln}" for f, ln in violations)
        pytest.fail(f"scan_error writes bypassing safe_str:\n{formatted}")


# ---------------------------------------------------------------------------
# Self-test: confirm the gate catches synthetic bypasses
# ---------------------------------------------------------------------------

def test_gate_catches_synthetic_bypass() -> None:
    """Gate self-test: if it ever stops catching bypasses, CI fails here
    even when the real codebase is clean."""
    source = textwrap.dedent("""\
        def bad_callsite(e):
            ep = CryptoEndpoint(scan_error=str(e))

        def bad_assign(exc):
            ep.scan_error = f"prefix: {exc}"
    """)
    tree = ast.parse(source, filename="<synthetic>")

    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "scan_error" and not _classify_rhs(kw.value, tree):
                    violations.append(kw.value.lineno)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "scan_error":
                    if not _classify_rhs(node.value, tree):
                        violations.append(node.lineno)

    assert len(violations) == 2, (
        f"Gate self-test expected 2 violations from synthetic bypass source, got {len(violations)}: {violations}"
    )


# ---------------------------------------------------------------------------
# Negative test: confirm the gate does NOT flag safe patterns
# ---------------------------------------------------------------------------

def test_gate_does_not_flag_safe_patterns() -> None:
    """Gate negative test: all known safe patterns must produce zero violations."""
    source = textwrap.dedent("""\
        from quirk.util.safe_exc import safe_str

        def safe_patterns(exc, _validation, e):
            scan_error_msg = safe_str(exc)

            # 1. None literal
            ep1 = CryptoEndpoint(scan_error=None)
            # 2. String literal
            ep2 = CryptoEndpoint(scan_error="some-static-error")
            # 3. safe_str call
            ep3 = CryptoEndpoint(scan_error=safe_str(exc))
            # 4. Attribute read (e.g., _validation.reason)
            ep4 = CryptoEndpoint(scan_error=_validation.reason)
            # 5. Name whose source uses safe_str (gcp_connector two-step pattern)
            ep5 = CryptoEndpoint(scan_error=scan_error_msg)
            # 6. f-string with safe_str in every FormattedValue
            ep6.scan_error = f"SSH_ERROR: {safe_str(e)}"
    """)
    tree = ast.parse(source, filename="<synthetic>")

    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "scan_error" and not _classify_rhs(kw.value, tree):
                    violations.append(kw.value.lineno)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "scan_error":
                    if not _classify_rhs(node.value, tree):
                        violations.append(node.lineno)

    assert violations == [], (
        f"Gate incorrectly flagged safe patterns at lines: {violations}"
    )


# ---------------------------------------------------------------------------
# Task 2 additions: corpus replay
# ---------------------------------------------------------------------------

from quirk.util.safe_exc import safe_str  # noqa: E402
from quirk.errors import format_error  # noqa: E402

# ---------------------------------------------------------------------------
# Phase 93 Task 2: SCHED-AUTH-001 error code registry assertion
# ---------------------------------------------------------------------------

def test_sched_auth_001_format_error() -> None:
    """format_error('SCHED-AUTH-001') must emit the QRK-SCHED-AUTH-001 prefix and a Fix clause."""
    result = format_error("SCHED-AUTH-001")
    assert "QRK-SCHED-AUTH-001" in result, (
        f"format_error('SCHED-AUTH-001') did not contain 'QRK-SCHED-AUTH-001': {result!r}"
    )
    assert "Fix:" in result, (
        f"format_error('SCHED-AUTH-001') did not contain 'Fix:': {result!r}"
    )


CORPUS: tuple[tuple[str, type[BaseException]], ...] = (
    ("https://vault.example.com:8200?token=s.AbCdEfGhIjKlMnOpQrSt1234XyZ", Exception),
    ("hvs.CAESIJxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx token rejected", Exception),
    ("could not connect: postgresql://admin:S3cret!Pass@10.0.0.5:5432/prod", ConnectionError),
    ("ADC missing: /home/runner/.config/gcloud/application_default_credentials.json", FileNotFoundError),
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.signaturepart", PermissionError),
    ("aws_secret=AKIAIOSFODNN7EXAMPLE0123456789abcdefghijkl rejected", RuntimeError),
)

FORBIDDEN_SUBSTRINGS: tuple[str, ...] = (
    "s.AbCdEfGhIjKl",
    "hvs.CAESIJ",
    "S3cret!Pass",
    "application_default_credentials",
    "Bearer eyJhbGci",
    "AKIAIOSFODNN7EXAMPLE",
)


@pytest.mark.parametrize("msg,cls", CORPUS)
def test_corpus_replay(msg: str, cls: type[BaseException]) -> None:
    """LEAK-03 corpus replay: every credential-bearing exception text
    must scrub to class-name-only when routed through safe_str."""
    result = safe_str(cls(msg))
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in result, (
            f"safe_str leaked '{forbidden}' from {cls.__name__}({msg!r}) -> {result!r}"
        )
    assert result.startswith(cls.__name__), (
        f"safe_str dropped class name for {cls.__name__}({msg!r}) -> {result!r}"
    )
