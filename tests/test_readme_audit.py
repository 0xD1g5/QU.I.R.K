"""Offline tests for scripts/readme_audit.py (command enumeration, link
extraction, exit-code contract). No test here opens a socket: every link check
goes through an injected fetcher.
"""
from __future__ import annotations

import builtins
import json
import re
import sys
import urllib.error
from pathlib import Path

import pytest

from scripts import readme_audit
from tests.test_readme_links_pinned import markdown_it_urls

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


def _commands():
    return readme_audit.enumerate_commands(README.read_text(encoding="utf-8"))


def test_commands_include_quick_start():
    cmds = _commands()
    texts = [c["text"] for c in cmds]
    assert any("pip install 'quirk-scanner[all]'" in t for t in texts)
    assert any("quirk serve" in t for t in texts)
    assert all(isinstance(c["line"], int) and c["line"] > 0 for c in cmds)


def test_commands_cover_every_bash_fence():
    text = README.read_text(encoding="utf-8")
    opened = re.findall(r"^\s{0,3}```(?:bash|sh|shell|console)\b", text, re.M)
    fence_ids = {c["fence_id"] for c in _commands() if c["kind"] == "fence"}
    assert len(opened) == len(fence_ids) > 0


def test_commands_cli_prints_json(capsys):
    assert readme_audit.main(["commands", "--readme", str(README)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["commands"]) >= 5


def test_links_file_mode_matches_markdown_it(tmp_path, capsys):
    text = README.read_text(encoding="utf-8")
    expected = {
        u for u in markdown_it_urls(text)
        if u and not u.startswith(("#", "mailto:"))
    }
    seen = []

    def fetcher(url, timeout):
        seen.append(url)
        return 200

    rc = readme_audit.main(
        ["links", "--source", f"file:{README}"], fetcher=fetcher)
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert set(report["ok"]) == expected
    assert set(seen) == expected


def _write(tmp_path, body):
    p = tmp_path / "R.md"
    p.write_text(body, encoding="utf-8")
    return f"file:{p}"


def test_links_exit_codes(tmp_path, capsys):
    src = _write(tmp_path, "[a](https://example.com/a) [b](https://example.com/b)\n")
    assert readme_audit.main(["links", "--source", src],
                             fetcher=lambda u, t: 200) == 0
    capsys.readouterr()

    rc = readme_audit.main(
        ["links", "--source", src],
        fetcher=lambda u, t: 404 if u.endswith("/b") else 200)
    report = json.loads(capsys.readouterr().out)
    assert rc == 1 and report["verdict"] == "red"
    assert [b["url"] for b in report["broken"]] == ["https://example.com/b"]

    def boom(u, t):
        raise urllib.error.URLError("offline")

    rc = readme_audit.main(["links", "--source", src], fetcher=boom)
    report = json.loads(capsys.readouterr().out)
    assert rc == 2 and report["verdict"] == "unknown"


def test_links_unknown_beats_green(tmp_path, capsys):
    src = _write(tmp_path, "[a](https://example.com/a) [b](https://example.com/b)\n")

    def mixed(u, t):
        if u.endswith("/b"):
            raise urllib.error.URLError("x")
        return 200

    assert readme_audit.main(["links", "--source", src], fetcher=mixed) == 2


def test_relative_links_are_broken(tmp_path, capsys):
    src = _write(tmp_path, "[d](docs/x.md)\n")
    rc = readme_audit.main(["links", "--source", src], fetcher=lambda u, t: 200)
    report = json.loads(capsys.readouterr().out)
    assert rc == 1 and report["broken"][0]["url"] == "docs/x.md"


def test_links_substitute_ref(tmp_path, capsys):
    body = (
        "[a](https://github.com/o/r/blob/v1.2.3/docs/a.md) "
        "![i](https://raw.githubusercontent.com/o/r/v1.2.3/img.png)\n"
    )
    seen = []

    def fetcher(url, timeout):
        seen.append(url)
        return 200

    rc = readme_audit.main(
        ["links", "--source", _write(tmp_path, body),
         "--substitute-ref", "abc123"], fetcher=fetcher)
    assert rc == 0
    assert sorted(seen) == [
        "https://github.com/o/r/blob/abc123/docs/a.md",
        "https://raw.githubusercontent.com/o/r/abc123/img.png",
    ]


def test_pypi_mode_without_renderer_is_unknown(monkeypatch, capsys):
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("readme_renderer"):
            raise ImportError("no renderer")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.delitem(sys.modules, "readme_renderer", raising=False)
    monkeypatch.delitem(sys.modules, "readme_renderer.markdown", raising=False)
    rc = readme_audit.main(
        ["links", "--source", "pypi:1.0.0"],
        fetcher=lambda u, t: 200,
        json_loader=lambda v, t: {"info": {"description": "[a](https://e.com)"}})
    report = json.loads(capsys.readouterr().out)
    assert rc == 2 and report["verdict"] == "unknown"


def test_commands_blocks_and_python_range(capsys):
    cmds = _commands()
    clone_fence = {c["fence_id"] for c in cmds if c["text"].startswith("git clone")}
    assert clone_fence
    assert all(c["block"] == "contributor"
               for c in cmds if c["fence_id"] in clone_fence)
    assert any(c["block"] == "user" and "quirk serve" in c["text"] for c in cmds)
    assert readme_audit.stated_python_range("needs Python 3.10 to 3.14.") == "3.10-3.14"
    assert readme_audit.stated_python_range("Python 3.10–3.14") == "3.10-3.14"
    assert readme_audit.stated_python_range("no range here") is None
    assert readme_audit.main(["commands", "--readme", str(README)]) == 0
    assert "python_range" in json.loads(capsys.readouterr().out)
