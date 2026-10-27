"""Shared, Python-3.10-safe reader for the ``[project]`` version in pyproject.toml.

Phase 232 D-06 (todo 261015 WR-03). ``pyproject.toml`` declares
``requires-python = ">=3.10"``, but ``tomllib`` only exists from 3.11. The tests
that derive the release tag from the pyproject version (the README brand-logo
and hero tests) used to ``import tomllib`` at module top level, so they could
not even be imported on 3.10. CI runs 3.11 only, so nothing would catch that.

``pyproject_version()`` tries ``tomllib``, then the ``tomli`` backport, then a
strict regex on the ``[project]`` table's ``version = "..."`` line. The regex
tier raises ``ValueError`` rather than guessing when the table or line is
missing. All imports happen inside the function, so this module imports on 3.10.

Production ``quirk/__init__.py`` keeps its own ``tomllib`` import on the
unpackaged dev path on purpose; D-06 leaves it alone.

This module has no ``test_`` prefix, so pytest never collects it (same
convention as ``tests/cli_helpers.py``).
"""
from __future__ import annotations

import re
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

_PROJECT_HDR = re.compile(r"^\[project\]\s*$", re.M)
_NEXT_HDR = re.compile(r"^\[", re.M)
_VERSION = re.compile(r'^version\s*=\s*"([^"]+)"\s*$', re.M)


def _version_from_text(text: str) -> str:
    """Return the ``[project]`` version from pyproject text, or raise ValueError."""
    m = _PROJECT_HDR.search(text)
    if not m:
        raise ValueError("pyproject.toml has no [project] table")
    body = text[m.end():]
    nxt = _NEXT_HDR.search(body)
    table = body[: nxt.start()] if nxt else body
    v = _VERSION.search(table)
    if not v:
        raise ValueError("pyproject.toml [project] table has no version line")
    return v.group(1)


def pyproject_version(path: Path = PYPROJECT) -> str:
    """Return ``[project].version`` via tomllib, then tomli, then the regex tier."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        import tomllib as _toml
    except ImportError:
        try:
            import tomli as _toml  # type: ignore[no-redef]
        except ImportError:
            return _version_from_text(text)
    return _toml.loads(text)["project"]["version"]
