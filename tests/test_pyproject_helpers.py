"""Tests for ``tests/pyproject_helpers.py`` (Phase 232 D-06, todo 261015 WR-03).

Each of the helper's three tiers (``tomllib``, ``tomli``, strict regex) must
return the same version as ``tomllib`` does for the real ``pyproject.toml``,
and the regex tier must refuse to guess when the ``[project]`` table or its
``version =`` line is missing.
"""
from __future__ import annotations

import sys
import types

import pytest

from tests.pyproject_helpers import PYPROJECT, _version_from_text, pyproject_version

tomllib = pytest.importorskip("tomllib")


def _real_text() -> str:
    return PYPROJECT.read_text(encoding="utf-8")


def _real_version() -> str:
    return tomllib.loads(_real_text())["project"]["version"]


def test_regex_tier_agrees_with_tomllib():
    assert _version_from_text(_real_text()) == _real_version()


def test_regex_tier_raises_without_project_table():
    text = '[tool.x]\nversion = "9.9.9"\n'
    with pytest.raises(ValueError, match=r"\[project\]"):
        _version_from_text(text)


def test_regex_tier_ignores_version_outside_project_table():
    text = (
        '[project]\nname = "x"\n\n'
        '[tool.x]\nversion = "9.9.9"\n'
    )
    with pytest.raises(ValueError, match="version"):
        _version_from_text(text)


def test_tomli_tier(monkeypatch):
    real_loads = tomllib.loads
    monkeypatch.setitem(sys.modules, "tomllib", None)
    monkeypatch.setitem(sys.modules, "tomli", types.SimpleNamespace(loads=real_loads))
    assert pyproject_version() == _real_version()


def test_regex_tier_via_pyproject_version(monkeypatch):
    expected = _real_version()
    monkeypatch.setitem(sys.modules, "tomllib", None)
    monkeypatch.setitem(sys.modules, "tomli", None)
    assert pyproject_version() == expected


def test_explicit_path(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nname = "demo"\nversion = "1.2.3"\n', encoding="utf-8")
    assert pyproject_version(p) == "1.2.3"


def test_explicit_path_regex_tier(tmp_path, monkeypatch):
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nname = "demo"\nversion = "1.2.3"\n', encoding="utf-8")
    monkeypatch.setitem(sys.modules, "tomllib", None)
    monkeypatch.setitem(sys.modules, "tomli", None)
    assert pyproject_version(p) == "1.2.3"
