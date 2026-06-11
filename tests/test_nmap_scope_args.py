"""
Tests for Phase 121-01 — nmap arg construction per port scope (PORT-06).

Covers:
- 'top1000' scope passes --top-ports 1000 to nmap; no -p <csv> form
- 'all' scope passes -p- to nmap; no -p <csv> form
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quirk.discovery.nmap_provider import run_nmap_discovery


def test_top1000_scope_uses_top_ports_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """port_spec_override='--top-ports 1000' results in --top-ports + 1000 in nmap argv (PORT-06)."""
    captured: dict = {}

    def fake_run(args, **kwargs):  # noqa: ANN001
        captured["args"] = list(args)
        raise FileNotFoundError("nmap not found — test sentinel")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(Exception):
        run_nmap_discovery(
            ["127.0.0.1"],
            ports=[],
            output_dir=str(tmp_path),
            port_spec_override="--top-ports 1000",
        )

    assert captured, "subprocess.run was not called"
    assert "--top-ports" in captured["args"]
    assert "1000" in captured["args"]
    # Must NOT use the -p <csv> form
    assert "-p" not in captured["args"]


def test_all_scope_uses_dash_p_dash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """port_spec_override='-p-' results in -p- in nmap argv (PORT-06)."""
    captured: dict = {}

    def fake_run(args, **kwargs):  # noqa: ANN001
        captured["args"] = list(args)
        raise FileNotFoundError("nmap not found — test sentinel")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(Exception):
        run_nmap_discovery(
            ["127.0.0.1"],
            ports=[],
            output_dir=str(tmp_path),
            port_spec_override="-p-",
        )

    assert captured, "subprocess.run was not called"
    assert "-p-" in captured["args"]
