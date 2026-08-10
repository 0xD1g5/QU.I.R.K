"""Phase 146 Plan 04 (DISC-04/DISC-05/DISC-06, D-01/D-02/D-03/D-05/D-07/D-13):
tests for the instrumented run_scan.py discovery batch loop — per-batch
progress writes, exact hosts-checked accounting, batch-scaled timeout/timing,
and the CLI progress line.

Part A mirrors the loop shape (following tests/test_liveness_prepass.py's
convention) with stubbed nmap calls — no subprocess is spawned and no real
nmap binary is required.

Part B parses the REAL run_scan.py (and reads the real jobs.py) via `ast` so
a passing mirror test can never mask an unwired loop (mirrors
tests/test_cli_dashboard_discovery_parity.py's structural-test convention).
"""
from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest

from quirk.discovery.nmap_provider import (
    discovery_timeout_for_batch,
    discovery_timing_template_for_batch,
)
from quirk.scanner.target_expander import _chunked, _expand_and_dedup_hosts, _MAX_HOSTS_PER_CIDR

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SCAN_PATH = _REPO_ROOT / "run_scan.py"
_JOBS_ROUTE_PATH = _REPO_ROOT / "quirk" / "dashboard" / "api" / "routes" / "jobs.py"


class _FakeHostStatus:
    def __init__(self, host: str, up: bool):
        self.host = host
        self.up = up


def _run_batched_discovery_with_progress(
    host_tokens: List[str],
    liveness_fn,
    sweep_fn,
    progress_writer,
    chunk_size: int = _MAX_HOSTS_PER_CIDR,
):
    """Mirrors run_scan.py's instrumented discovery batch loop exactly
    (Phase 146 / Plan 04): pre-count batch total, per-batch liveness
    pre-pass + sweep, per-batch timeout/timing computed from len(batch), and
    per-batch progress bookkeeping on ALL THREE paths (normal, fully-dead,
    failed) — never gated behind a `continue`.

    Returns (batch_total, hosts_checked, progress_calls, timeout_calls,
    timing_calls).
    """
    total_hosts = sum(1 for _ in _expand_and_dedup_hosts(host_tokens))
    batch_total = math.ceil(total_hosts / chunk_size) or 1

    hosts_checked = 0
    progress_calls: List[tuple] = []
    timeout_calls: List[int] = []
    timing_calls: List[str] = []

    batch_num = 0
    host_iter = _expand_and_dedup_hosts(host_tokens)
    for batch in _chunked(host_iter, chunk_size):
        batch_num += 1

        batch_timeout = discovery_timeout_for_batch(len(batch))
        batch_timing = discovery_timing_template_for_batch(len(batch))
        timeout_calls.append(batch_timeout)
        timing_calls.append(batch_timing)

        try:
            statuses = liveness_fn(batch, timeout=batch_timeout)
        except RuntimeError:
            sweep_targets = batch
        else:
            down_hosts = {s.host for s in statuses if not s.up}
            sweep_targets = [h for h in batch if h not in down_hosts]

        if sweep_targets:
            try:
                sweep_fn(sweep_targets, timeout=batch_timeout, timing=batch_timing)
            except RuntimeError:
                pass

        # Bookkeeping runs on every path.
        hosts_checked += len(batch)
        progress_writer(batch_num, batch_total, hosts_checked)

    return batch_total, hosts_checked, progress_calls, timeout_calls, timing_calls


# ---------------------------------------------------------------------------
# Part A: mirror-shape behavior tests
# ---------------------------------------------------------------------------

def test_batch_total_and_exact_hosts_checked_on_partial_final_batch():
    """D-02 regression guard: hosts_checked must be the EXACT total, never
    batch_total * _MAX_HOSTS_PER_CIDR, on a host count that is not a
    multiple of the chunk size."""
    chunk_size = 10
    # 23 hosts -> 3 batches (10, 10, 3), NOT a multiple of chunk_size.
    hosts = [f"10.0.0.{i}" for i in range(1, 24)]
    assert len(hosts) == 23

    def liveness_fn(batch, timeout):
        return [_FakeHostStatus(h, up=True) for h in batch]

    def sweep_fn(targets, timeout, timing):
        return list(targets)

    calls = []

    def progress_writer(batch_num, batch_total, hosts_checked):
        calls.append((batch_num, batch_total, hosts_checked))

    batch_total, hosts_checked, _, _, _ = _run_batched_discovery_with_progress(
        hosts, liveness_fn, sweep_fn, progress_writer, chunk_size=chunk_size
    )

    assert batch_total == math.ceil(23 / chunk_size)
    assert batch_total == 3
    assert hosts_checked == 23
    # The D-02 regression this guards against: batch_total * chunk_size
    # would be 30, not 23.
    assert hosts_checked != batch_total * chunk_size
    assert calls[-1] == (3, 3, 23)


def test_progress_recorded_once_per_batch_across_all_three_paths():
    """Three batches: one normal, one fully-dead (all hosts liveness-skipped,
    no sweep call), one whose sweep raises RuntimeError. All three must
    still produce exactly one progress record each."""
    chunk_size = 2
    # batch 1: 10.0.0.1 (up), 10.0.0.2 (up)      -> normal sweep
    # batch 2: 10.0.0.3 (down), 10.0.0.4 (down)  -> fully-dead, no sweep call
    # batch 3: 10.0.0.5 (up), 10.0.0.6 (up)      -> sweep raises RuntimeError
    hosts = [f"10.0.0.{i}" for i in range(1, 7)]
    dead = {"10.0.0.3", "10.0.0.4"}
    fail_batch_hosts = {"10.0.0.5", "10.0.0.6"}

    def liveness_fn(batch, timeout):
        return [_FakeHostStatus(h, up=(h not in dead)) for h in batch]

    sweep_calls = []

    def sweep_fn(targets, timeout, timing):
        sweep_calls.append(list(targets))
        if set(targets) == fail_batch_hosts:
            raise RuntimeError("discovery failed")
        return list(targets)

    calls = []

    def progress_writer(batch_num, batch_total, hosts_checked):
        calls.append((batch_num, batch_total, hosts_checked))

    batch_total, hosts_checked, _, _, _ = _run_batched_discovery_with_progress(
        hosts, liveness_fn, sweep_fn, progress_writer, chunk_size=chunk_size
    )

    assert batch_total == 3
    assert len(calls) == 3, "expected one progress record per batch, including dead and failed batches"
    assert hosts_checked == 6
    # Only 2 sweep calls made (batch 2 fully-dead skips the sweep entirely).
    assert len(sweep_calls) == 2


def test_batch_timeout_and_timing_template_derive_from_batch_size():
    """The timeout/timing passed to the stubbed nmap calls must come from
    discovery_timeout_for_batch()/discovery_timing_template_for_batch() and
    differ between a full _MAX_HOSTS_PER_CIDR-sized batch and a small final
    partial batch."""
    chunk_size = _MAX_HOSTS_PER_CIDR
    # 1024 + 5 hosts -> batch 1 full-size (1024), batch 2 tiny (5).
    hosts = [f"10.{i // 256}.{(i // 16) % 16}.{i % 16}" for i in range(1029)]

    def liveness_fn(batch, timeout):
        return [_FakeHostStatus(h, up=True) for h in batch]

    def sweep_fn(targets, timeout, timing):
        return list(targets)

    def progress_writer(batch_num, batch_total, hosts_checked):
        pass

    batch_total, hosts_checked, _, timeout_calls, timing_calls = _run_batched_discovery_with_progress(
        hosts, liveness_fn, sweep_fn, progress_writer, chunk_size=chunk_size
    )

    assert len(timeout_calls) == 2
    assert len(timing_calls) == 2
    assert timeout_calls[0] == discovery_timeout_for_batch(1024)
    assert timeout_calls[1] == discovery_timeout_for_batch(5)
    assert timeout_calls[0] != timeout_calls[1]
    assert timing_calls[0] == discovery_timing_template_for_batch(1024)
    assert timing_calls[1] == discovery_timing_template_for_batch(5)
    assert timing_calls[0] != timing_calls[1]


# ---------------------------------------------------------------------------
# Part B: structural assertions against the real run_scan.py / jobs.py source
# ---------------------------------------------------------------------------

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


def test_update_batch_progress_called_once_inside_chunked_loop():
    """update_batch_progress must appear exactly once as a call, and that
    call must be lexically inside the `for batch in _chunked(...)` loop —
    proving the real loop (not a copy) is wired."""
    _, tree = _parse_run_scan()

    chunked_for_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.For)
        and isinstance(node.iter, ast.Call)
        and isinstance(node.iter.func, ast.Name)
        and node.iter.func.id == "_chunked"
    ]
    assert chunked_for_nodes, "No `for batch in _chunked(...)` loop found in run_scan.py"

    calls = _find_calls(tree, "update_batch_progress")
    assert len(calls) == 1, (
        f"Expected exactly 1 update_batch_progress(...) call site in "
        f"run_scan.py, found {len(calls)}."
    )

    call = calls[0]
    inside_a_chunked_loop = any(call in ast.walk(loop_node) for loop_node in chunked_for_nodes)
    assert inside_a_chunked_loop, (
        "update_batch_progress(...) must be lexically inside the "
        "`for batch in _chunked(...)` loop."
    )


def test_neither_nmap_call_uses_args_nmap_timeout_as_timeout_seconds():
    """Neither run_nmap_discovery nor run_nmap_liveness_check may be called
    with a `timeout_seconds` keyword whose value is `args.nmap_timeout` — the
    Pitfall-2 guard that the formula's output must fully replace the static
    CLI default inside the batch loop."""
    _, tree = _parse_run_scan()

    offending = []
    for func_name in ("run_nmap_discovery", "run_nmap_liveness_check"):
        for call in _find_calls(tree, func_name):
            for kw in call.keywords:
                if kw.arg != "timeout_seconds":
                    continue
                value = kw.value
                if (
                    isinstance(value, ast.Attribute)
                    and value.attr == "nmap_timeout"
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "args"
                ):
                    offending.append(func_name)

    assert not offending, (
        f"Found timeout_seconds=args.nmap_timeout on: {offending}. The "
        f"batch-scaled timeout formula must fully replace the static CLI "
        f"default inside the batch loop (Pitfall 2)."
    )


def test_jobs_route_has_no_static_nmap_timeout_token():
    """quirk/dashboard/api/routes/jobs.py must contain no --nmap-timeout
    token — the Pitfall-2 guard that fails if a future change reintroduces a
    static subprocess timeout that could silently override the per-batch
    formula."""
    source = _JOBS_ROUTE_PATH.read_text()
    assert "--nmap-timeout" not in source, (
        "quirk/dashboard/api/routes/jobs.py must not pass a static "
        "--nmap-timeout token to the spawned run_scan.py subprocess — the "
        "per-batch timeout is computed inside run_scan.py itself."
    )
