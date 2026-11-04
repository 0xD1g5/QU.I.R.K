"""Red-on-defect tests for scripts/score_attribution.py (HARNESS-05, WR-04)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score_attribution.py"
LEGACY = "Legacy TLS versions allowed (TLS 1.0/1.1)"


def _load():
    spec = importlib.util.spec_from_file_location("score_attribution_t", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sa = _load()


def _bridge():
    def canonical(title):
        return LEGACY if title.startswith("Legacy TLS version: ") else None
    return sa.Bridge({"Legacy TLS version: ": {}}, {}, canonical)


LEGACY_DASH = ("Legacy TLS version: TLSv1.0", LEGACY, "HIGH")


def test_missing_dashboard_score_hard_fails():
    lines, ok = sa.evaluate(84, 84, None, [], [], _bridge(), [],
                            sa._STUB_CONSTANTS)
    assert ok is False
    assert "SCORE-PARITY: FAIL dashboard score missing" in lines


def test_81_point_gap_attributed_to_one_severity_difference_fails():
    lines, ok = sa.evaluate(84, 84, 3, [LEGACY_DASH], [(LEGACY, "LOW")],
                            _bridge(), [], sa._STUB_CONSTANTS)
    assert ok is False
    assert any(l.startswith("GAP-BOUND: gap=81 bound=43 items=1")
               for l in lines)


def test_in_bound_gap_still_passes():
    lines, ok = sa.evaluate(84, 84, 69, [LEGACY_DASH], [(LEGACY, "LOW")],
                            _bridge(), [], sa._STUB_CONSTANTS)
    assert ok is True
    assert any(l.startswith("GAP-BOUND: gap=15 bound=43 items=1")
               for l in lines)


@pytest.mark.parametrize("a,b,expected", [
    ("CRITICAL", "absent", 78), ("HIGH", "absent", 43),
    ("CRITICAL", "HIGH", 47), ("MEDIUM", "LOW", 12),
])
def test_item_bounds(a, b, expected):
    assert sa._item_bound(a, b, sa._STUB_CONSTANTS) == expected


def test_constants_none_fails_closed():
    lines, ok = sa.evaluate(84, 84, 69, [LEGACY_DASH], [(LEGACY, "LOW")],
                            _bridge(), [], None)
    assert ok is False
    assert any("SCORE-PARITY: FAIL bound unavailable" in l for l in lines)


def test_stub_constants_match_live_scoring():
    live = sa.load_constants()
    assert live is not None
    assert sa._STUB_CONSTANTS == live


def test_load_constants_none_when_scoring_unimportable(monkeypatch):
    monkeypatch.setitem(sys.modules, "quirk.intelligence.scoring", None)
    monkeypatch.setitem(sys.modules, "quirk.intelligence", None)
    assert sa.load_constants() is None


def test_self_test_runs_with_quirk_unimportable(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "quirk", None)
    assert sa.self_test() == 0
    assert "self-test: 6/6" in capsys.readouterr().out


def test_self_test_under_host_python_isolated():
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--self-test"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert r.stdout.strip().splitlines()[-1] == "self-test: 6/6"
