"""Phase 146 Plan 02 (DISC-06 / D-12): structural regression test locking CLI
and dashboard onto one shared nmap discovery call site.

This is a structural test, not a runtime test — it never imports run_scan or
spawns any process. It reads run_scan.py and quirk/dashboard/api/routes/jobs.py
from disk as text/AST and asserts the invariants that guarantee CLI and
dashboard discovery share exactly one implementation:

1. Exactly one `run_nmap_discovery(...)` call site in run_scan.py.
2. Exactly one `run_nmap_liveness_check(...)` call site in run_scan.py.
3. The dashboard's job-spawn command routes through the same `run_scan`
   module (`-m run_scan`), proving it reuses the CLI entry point rather than
   forking its own discovery path.
4. The single `run_nmap_discovery` call is lexically inside the Phase 144
   chunked batch loop (the `for` node iterating over `_chunked(...)`).
5. `quirk/dashboard/api/routes/jobs.py` contains zero occurrences of the
   literal substring `"run_nmap_discovery("` — closing the gap where the
   dashboard route could add a second, independent discovery call site in
   addition to spawning the run_scan subprocess.

Node IDs:
  test_exactly_one_run_nmap_discovery_call_site
  test_exactly_one_run_nmap_liveness_check_call_site
  test_dashboard_spawns_run_scan_module
  test_run_nmap_discovery_call_is_inside_chunked_batch_loop
  test_dashboard_jobs_route_has_no_direct_discovery_call
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SCAN_PATH = _REPO_ROOT / "run_scan.py"
_JOBS_ROUTE_PATH = _REPO_ROOT / "quirk" / "dashboard" / "api" / "routes" / "jobs.py"


def _parse_run_scan():
    source = _RUN_SCAN_PATH.read_text()
    return source, ast.parse(source, filename=str(_RUN_SCAN_PATH))


def _find_calls(tree: ast.AST, func_name: str):
    calls = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == func_name
        ):
            calls.append(node)
    return calls


def test_exactly_one_run_nmap_discovery_call_site():
    """A second `run_nmap_discovery` call site means CLI and dashboard
    discovery have forked and DISC-06's shared implementation guarantee is
    broken."""
    _, tree = _parse_run_scan()
    calls = _find_calls(tree, "run_nmap_discovery")
    assert len(calls) == 1, (
        f"Expected exactly 1 run_nmap_discovery(...) call site in run_scan.py, "
        f"found {len(calls)}. A second call site means CLI and dashboard "
        f"discovery have forked and DISC-06's shared implementation "
        f"guarantee is broken."
    )


def test_exactly_one_run_nmap_liveness_check_call_site():
    """Same guarantee as above, for the Phase 145 liveness pre-pass."""
    _, tree = _parse_run_scan()
    calls = _find_calls(tree, "run_nmap_liveness_check")
    assert len(calls) == 1, (
        f"Expected exactly 1 run_nmap_liveness_check(...) call site in "
        f"run_scan.py, found {len(calls)}. A second call site means CLI and "
        f"dashboard discovery have forked and DISC-06's shared "
        f"implementation guarantee is broken."
    )


def test_dashboard_spawns_run_scan_module():
    """The dashboard's subprocess command must route through the same
    `run_scan` module the CLI uses, tolerant of whitespace/line breaks."""
    source = _JOBS_ROUTE_PATH.read_text()
    pattern = re.compile(r'"-m"\s*,\s*"run_scan"', re.MULTILINE)
    assert pattern.search(source), (
        "jobs.py must spawn the CLI entry point via [\"-m\", \"run_scan\"] — "
        "a future change spawning a different entry point breaks DISC-06 "
        "parity."
    )


def test_run_nmap_discovery_call_is_inside_chunked_batch_loop():
    """Prevents a regression that moves discovery back outside the Phase 144
    chunked batch loop."""
    _, tree = _parse_run_scan()

    chunked_for_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            call = node.iter
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "_chunked"
            ):
                chunked_for_nodes.append(node)

    assert chunked_for_nodes, "No `for batch in _chunked(...)` loop found in run_scan.py"

    discovery_calls = _find_calls(tree, "run_nmap_discovery")
    assert len(discovery_calls) == 1
    discovery_call = discovery_calls[0]

    inside_a_chunked_loop = any(
        discovery_call in ast.walk(loop_node) for loop_node in chunked_for_nodes
    )
    assert inside_a_chunked_loop, (
        "run_nmap_discovery(...) must be lexically inside the `for batch in "
        "_chunked(...)` loop — a regression moving it outside would defeat "
        "the Phase 144 batch chunking."
    )


def test_dashboard_jobs_route_has_no_direct_discovery_call():
    """Without this test, a future change could add a second, independent
    run_nmap_discovery() call inside jobs.py in addition to still spawning
    the run_scan subprocess, and none of the tests above would catch it —
    CLI and dashboard would then run discovery through two different code
    paths in some cases, exactly what DISC-06 exists to prevent."""
    source = _JOBS_ROUTE_PATH.read_text()
    assert source.count("run_nmap_discovery(") == 0, (
        "quirk/dashboard/api/routes/jobs.py must never call "
        "run_nmap_discovery(...) directly — it must only route discovery "
        "through the `-m run_scan` subprocess spawn, matching the CLI's "
        "single call site."
    )
