"""Phase 80 ADCS-09 — AST CI gate per D-80-R4.

`quirk/scanner/adcs_scanner.py` must NEVER:
  - import `certipy` / `certipy_ad` / `impacket.ldap.ldapasn1_modify`
  - `from cryptography.x509 import CertificateSigningRequestBuilder`
  - call any `.add()` / `.modify()` / `.delete()` / `.modify_dn()`
    attribute-method on the bound ldap3 Connection (or anything else)

The static arm of ADCS-09 (paired with the runtime arm in
`tests/test_adcs_no_writes.py`). Modeled on the Phase 79
`tests/test_smime_ast_gate.py` walker.
"""
from __future__ import annotations

import ast
import pathlib
import textwrap

import pytest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = PROJECT_ROOT / "quirk" / "scanner" / "adcs_scanner.py"

FORBIDDEN_IMPORT_MODULES = {
    "certipy",
    "certipy_ad",
    "impacket.ldap.ldapasn1_modify",
}
FORBIDDEN_FROM_NAMES = {
    ("cryptography.x509", "CertificateSigningRequestBuilder"),
}
FORBIDDEN_LDAP_METHODS = {"add", "modify", "delete", "modify_dn"}


def _collect_violations(source: str, filename: str = "<source>") -> list[str]:
    """Walk the AST of `source` and return every D-80-R4 violation as a
    human-readable string. Empty list means clean."""
    violations: list[str] = []
    tree = ast.parse(source, filename=filename)

    # --- Walk Import / ImportFrom for forbidden module + name sets.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name in FORBIDDEN_IMPORT_MODULES or name.startswith("certipy"):
                    violations.append(f"import {name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_IMPORT_MODULES or mod.startswith("certipy"):
                violations.append(f"from {mod} import ...")
            for alias in node.names:
                if (mod, alias.name) in FORBIDDEN_FROM_NAMES:
                    violations.append(f"from {mod} import {alias.name}")

    # --- Walk Call nodes for any `<expr>.<method>(...)` whose attr name
    # is in FORBIDDEN_LDAP_METHODS. We only flag attribute-method CALLS
    # (Call.func is an ast.Attribute), not bare attribute access — this
    # avoids tripping on plain attribute reads or non-call references.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_LDAP_METHODS:
                violations.append(f".{node.func.attr}() method call")

    return violations


# ---------------------------------------------------------------------------
# Main gate: the real adcs_scanner.py module
# ---------------------------------------------------------------------------

def test_adcs_scanner_has_no_forbidden_writes_or_imports() -> None:
    """ADCS-09 / D-80-R4 — the production scanner module must be clean."""
    assert TARGET.exists(), f"adcs_scanner.py missing: {TARGET}"
    violations = _collect_violations(
        TARGET.read_text(encoding="utf-8"), filename=str(TARGET),
    )
    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        pytest.fail(
            "ADCS-09 violation in "
            f"{TARGET.relative_to(PROJECT_ROOT)}:\n{formatted}"
        )


# ---------------------------------------------------------------------------
# Positive self-test — the gate MUST catch every forbidden shape
# ---------------------------------------------------------------------------

def test_gate_catches_synthetic_forbidden_imports_and_calls() -> None:
    """Synthetic source containing every forbidden shape — at least one
    violation per forbidden category must be reported."""
    source = textwrap.dedent(
        """\
        import certipy_ad
        import certipy
        from impacket.ldap.ldapasn1_modify import Modify
        from cryptography.x509 import CertificateSigningRequestBuilder
        conn.add(entry)
        conn.modify(dn, changes)
        conn.delete(dn)
        conn.modify_dn(dn, new_dn)
        """
    )
    violations = _collect_violations(source, filename="<synthetic-forbidden>")
    # Expected matches (lower bound — order-independent):
    #   - 2 plain imports: certipy_ad, certipy
    #   - 1 ImportFrom mod-level: impacket.ldap.ldapasn1_modify
    #   - 1 ImportFrom name-level: CertificateSigningRequestBuilder
    #   - 4 method-call attributes: add, modify, delete, modify_dn
    assert len(violations) >= 8, (
        f"Gate self-test expected >=8 violations, got {len(violations)}: "
        f"{violations}"
    )

    # Verify each forbidden category fired at least once.
    joined = "\n".join(violations)
    assert "certipy" in joined, f"certipy import not flagged: {violations}"
    assert "CertificateSigningRequestBuilder" in joined, (
        f"CSR builder import not flagged: {violations}"
    )
    for meth in FORBIDDEN_LDAP_METHODS:
        assert f".{meth}() method call" in joined, (
            f".{meth}() not flagged: {violations}"
        )


# ---------------------------------------------------------------------------
# Negative self-test — clean source must produce zero violations
# ---------------------------------------------------------------------------

def test_gate_does_not_flag_clean_module() -> None:
    """A clean ldap3 read-only module body must produce zero violations."""
    source = textwrap.dedent(
        """\
        from __future__ import annotations

        import json
        import logging
        from datetime import datetime, timezone

        import ldap3
        from cryptography.x509 import load_der_x509_certificate
        from cryptography.hazmat.primitives.asymmetric import rsa, ec

        from quirk.models import CryptoEndpoint
        from quirk.util.weak_crypto import is_weak_cipher
        from quirk.util.safe_exc import safe_str

        def scan(conn):
            conn.bind()
            entries = conn.extend.standard.paged_search(
                search_base="dc=x",
                search_filter="(objectClass=*)",
                search_scope=ldap3.SUBTREE,
                attributes=["cn"],
            )
            conn.unbind()
            return entries
        """
    )
    violations = _collect_violations(source, filename="<synthetic-clean>")
    assert violations == [], (
        f"Gate incorrectly flagged clean ldap3 read-only source: {violations}"
    )
