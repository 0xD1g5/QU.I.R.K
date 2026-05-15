"""Phase 77 D-05 / scanners-protocol/IN-05: centralized PFS/weak helpers.

The local ``_is_pfs`` / ``_is_weak`` inner functions duplicated across
``broker_scanner``, ``email_scanner``, and ``tls_scanner`` are consolidated
into ``quirk/util/weak_crypto.py`` (Phase 73 home — Researcher Discretion
D-05) as module-level public helpers.
"""
from __future__ import annotations

import ast
import pathlib


def test_is_pfs_cipher_importable_and_correct() -> None:
    from quirk.util.weak_crypto import is_pfs_cipher

    assert is_pfs_cipher("ECDHE-RSA-AES128-GCM-SHA256") is True
    assert is_pfs_cipher("DHE-RSA-AES256-GCM-SHA384") is True
    assert is_pfs_cipher("AES128-SHA") is False
    assert is_pfs_cipher("") is False
    assert is_pfs_cipher(None) is False  # type: ignore[arg-type]


def test_is_weak_cipher_classification_importable_and_correct() -> None:
    from quirk.util.weak_crypto import is_weak_cipher_classification

    assert is_weak_cipher_classification("RC4-SHA") is True
    assert is_weak_cipher_classification("ECDHE-RSA-3DES-EDE-CBC-SHA") is True
    assert is_weak_cipher_classification("NULL-SHA") is True
    assert is_weak_cipher_classification("EXP-RC4-MD5") is True
    assert is_weak_cipher_classification("ECDHE-RSA-AES128-GCM-SHA256") is False
    assert is_weak_cipher_classification("") is False
    assert is_weak_cipher_classification(None) is False  # type: ignore[arg-type]


def _no_local_pfs_weak_funcs(path: str) -> None:
    src = pathlib.Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {"_is_pfs", "_is_weak"}:
            bad.append(f"{path}:{node.lineno}:{node.name}")
    assert not bad, (
        "Phase 77 D-05: local _is_pfs/_is_weak must be removed — found: "
        + ", ".join(bad)
    )


def test_broker_scanner_has_no_local_pfs_weak() -> None:
    _no_local_pfs_weak_funcs("quirk/scanner/broker_scanner.py")


def test_email_scanner_has_no_local_pfs_weak() -> None:
    _no_local_pfs_weak_funcs("quirk/scanner/email_scanner.py")


def test_tls_scanner_has_no_local_pfs_weak() -> None:
    _no_local_pfs_weak_funcs("quirk/scanner/tls_scanner.py")


def test_three_scanners_import_centralized_helpers() -> None:
    for path in (
        "quirk/scanner/broker_scanner.py",
        "quirk/scanner/email_scanner.py",
        "quirk/scanner/tls_scanner.py",
    ):
        src = pathlib.Path(path).read_text(encoding="utf-8")
        assert "from quirk.util.weak_crypto import" in src and "is_pfs_cipher" in src, (
            f"Phase 77 D-05: {path} must import is_pfs_cipher from quirk.util.weak_crypto"
        )
