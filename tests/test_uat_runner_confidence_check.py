"""Phase 240 D-24: UAT-8-02 must test the criterion (rate > 0.5 => confidence < 60), not just the range.

uat_runner.py is not importable under pytest (module-scope side effects), so the
verdict function is extracted with ast and exec'd in a fresh namespace.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parent.parent / "uat_runner.py"


def _load():
    src = RUNNER.read_text(encoding="utf-8")
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == "uat_8_02_verdict":
            ns: dict = {}
            exec(ast.get_source_segment(src, node), ns)  # noqa: S102
            return ns["uat_8_02_verdict"]
    pytest.fail("uat_runner.py has no module-level def uat_8_02_verdict")


def _d(conf, rate="absent"):
    d = {"confidence": {"confidence": conf}}
    if rate != "absent":
        d["evidence_summary"] = {"scan_error": {"rate": rate}}
    return d


def test_high_rate_high_confidence_fails():
    assert _load()(_d(79, 0.7097))[0] == "FAIL"


@pytest.mark.parametrize("conf,rate", [(59, 0.7097), (85, 0.2), (85, 0.5)])
def test_passing_cases(conf, rate):
    assert _load()(_d(conf, rate))[0] == "PASS"


@pytest.mark.parametrize("conf", [None, -1, 101])
def test_bad_confidence_fails(conf):
    assert _load()(_d(conf, 0.1))[0] == "FAIL"


def test_missing_rate_uses_range_only_and_says_so():
    status, notes, _ = _load()(_d(85))
    assert status == "PASS"
    assert "absent" in notes


def test_actual_string_has_rate_and_conf():
    actual = _load()(_d(59, 0.7))[2]
    assert "rate=" in actual and "conf=" in actual
