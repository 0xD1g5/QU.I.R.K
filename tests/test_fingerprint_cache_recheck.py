"""Phase 229 plan 02 (D-22): a cached fingerprint stage is not a recheck.

On the --cache --resume branch the fingerprint stage does no real work, so it
must not write run_stats["timings_sec"]["fingerprinting"]; otherwise the http
probe family would resolve healthy/no_targets from cached data and a plaintext
HTTP finding could be closed without a re-probe.
"""
from __future__ import annotations

import ast
from pathlib import Path

import run_scan
from quirk.intelligence.scope_signature import assess_probe_health, probe_family_rechecked
from tests.test_scan_scope_signature import _cfg


def test_phase_timer_mark_skipped_writes_no_key():
    stats = {"timings_sec": {}}
    with run_scan._phase_timer(stats, "fingerprinting") as t:
        t.mark_skipped()
    assert "fingerprinting" not in stats["timings_sec"]
    with run_scan._phase_timer(stats, "fingerprinting"):
        pass
    assert "fingerprinting" in stats["timings_sec"]


def _fingerprint_with_node():
    tree = ast.parse(Path(run_scan.__file__).read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            c = item.context_expr
            if (
                isinstance(c, ast.Call)
                and isinstance(c.func, ast.Name)
                and c.func.id == "_phase_timer"
                and len(c.args) >= 2
                and isinstance(c.args[1], ast.Constant)
                and c.args[1].value == "fingerprinting"
            ):
                found.append((node, item))
    return found


def test_cache_hit_branch_calls_mark_skipped_on_bound_timer():
    found = _fingerprint_with_node()
    assert len(found) == 1
    node, item = found[0]
    assert isinstance(item.optional_vars, ast.Name), "timer must be bound with `as`"
    name = item.optional_vars.id
    ifs = [
        n for n in ast.walk(node)
        if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == "fp_cached"
    ]
    assert ifs, "no `if fp_cached:` branch in the fingerprint stage"
    calls = [
        n for stmt in ifs[0].body for n in ast.walk(stmt)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "mark_skipped"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == name
    ]
    assert calls


def test_missing_fingerprinting_key_resolves_http_not_run():
    health = assess_probe_health(_cfg(), [], {"timings_sec": {}})
    assert health["http"]["status"] == "not_run"
    assert probe_family_rechecked(health, "http") is False
