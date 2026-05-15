"""Phase 77 D-07 / cbom-intel-reports/IN-01 — PLATFORM_VERSION single source.

Both `quirk/cbom/builder.py` and `quirk/reports/writer.py` must import
PLATFORM_VERSION from `quirk.__version__` rather than redefining a literal.
"""
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _module_source(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def _has_literal_assign(source: str, target_name: str) -> bool:
    """True if source contains a top-level `target_name = "<string literal>"` assignment."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == target_name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return True
    return False


def _imports_version_from_quirk(source: str) -> bool:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "quirk":
            for alias in node.names:
                if alias.name == "__version__":
                    return True
    return False


def test_cbom_builder_does_not_redefine_platform_version() -> None:
    src = _module_source("quirk/cbom/builder.py")
    assert not _has_literal_assign(src, "PLATFORM_VERSION"), (
        "quirk/cbom/builder.py must not redefine PLATFORM_VERSION as a literal "
        "(Phase 77 D-07 / IN-01 — single source via quirk.__version__)"
    )
    assert _imports_version_from_quirk(src), (
        "quirk/cbom/builder.py must `from quirk import __version__` (D-07)"
    )


def test_reports_writer_does_not_redefine_platform_version() -> None:
    src = _module_source("quirk/reports/writer.py")
    assert not _has_literal_assign(src, "PLATFORM_VERSION"), (
        "quirk/reports/writer.py must not redefine PLATFORM_VERSION as a literal "
        "(Phase 77 D-07 / IN-01 — single source via quirk.__version__)"
    )
    assert _imports_version_from_quirk(src), (
        "quirk/reports/writer.py must `from quirk import __version__` (D-07)"
    )


def test_platform_version_matches_canonical() -> None:
    """Consumers still see the canonical version after the import switch."""
    from quirk import __version__
    from quirk.cbom.builder import PLATFORM_VERSION as builder_ver
    from quirk.reports.writer import PLATFORM_VERSION as writer_ver

    assert builder_ver == __version__
    assert writer_ver == __version__
