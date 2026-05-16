"""Phase 79 SMIME-08 — AST CI gate that fails when any IMAP / SMTP /
POP / email.* import sneaks into `quirk/scanner/smime_scanner.py`.

The S/MIME scanner reads X.509 certificates from LDAP attributes only.
It must NEVER import a mail-protocol or envelope-parsing module — those
imports are the canary for "we accidentally started touching mailbox
content". This gate enforces the invariant at CI time.

Modeled on the Phase 59 `tests/test_scan_error_gate.py` AST walker
(PATTERNS.md authoritative analog).
"""
from __future__ import annotations

import ast
import pathlib
import textwrap

import pytest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = PROJECT_ROOT / "quirk" / "scanner" / "smime_scanner.py"

FORBIDDEN_MODULES = {"imaplib", "poplib", "smtplib", "email"}
FORBIDDEN_FROM_PREFIXES = ("email.",)


def _collect_violations(tree: ast.AST) -> list[str]:
    """Return a list of human-readable violation strings for every
    forbidden Import / ImportFrom node in the tree."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name in FORBIDDEN_MODULES or any(
                    name.startswith(p) for p in FORBIDDEN_FROM_PREFIXES
                ):
                    violations.append(f"import {name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_MODULES or any(
                mod.startswith(p) for p in FORBIDDEN_FROM_PREFIXES
            ):
                violations.append(f"from {mod} import ...")
    return violations


# ---------------------------------------------------------------------------
# Main gate: the real smime_scanner.py module
# ---------------------------------------------------------------------------

def test_smime_scanner_no_imap_or_envelope_imports() -> None:
    """SMIME-08 — quirk/scanner/smime_scanner.py must NOT import any
    IMAP, SMTP, POP, or email.* module."""
    assert TARGET.exists(), f"smime_scanner.py missing: {TARGET}"
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    violations = _collect_violations(tree)
    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        pytest.fail(
            "SMIME-08 violation — IMAP/SMTP/POP/email imports in "
            f"{TARGET.relative_to(PROJECT_ROOT)}:\n{formatted}"
        )


# ---------------------------------------------------------------------------
# Positive self-test — the gate MUST catch a synthetic forbidden import
# ---------------------------------------------------------------------------

def test_gate_catches_synthetic_forbidden_imports() -> None:
    """Self-test: synthesise a module body containing every shape of
    forbidden import and verify the gate flags ALL of them."""
    source = textwrap.dedent(
        """\
        import imaplib
        import poplib
        import smtplib
        import email
        from email.message import Message
        from email.header import Header
        """
    )
    tree = ast.parse(source, filename="<synthetic-forbidden>")
    violations = _collect_violations(tree)
    # 4 plain imports + 2 ImportFrom (email.message, email.header) = 6
    assert len(violations) == 6, (
        f"Gate self-test expected 6 violations, got {len(violations)}: {violations}"
    )


# ---------------------------------------------------------------------------
# Negative self-test — the gate must NOT flag clean module shape
# ---------------------------------------------------------------------------

def test_gate_does_not_flag_clean_module() -> None:
    """Self-test: a module body that imports only the legitimate
    crypto/LDAP dependencies must produce zero violations."""
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
        """
    )
    tree = ast.parse(source, filename="<synthetic-clean>")
    violations = _collect_violations(tree)
    assert violations == [], (
        f"Gate incorrectly flagged clean imports: {violations}"
    )
