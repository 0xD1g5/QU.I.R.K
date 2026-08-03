"""Phase 47 / Plan 02: tests for nmap_provider._default_nmap_args.

Tests lock in the D-07 requirement that --max-parallelism 100 is always
included in the default nmap argument list.

Phase 144 / Plan 02 (DISC-02, D-03/D-04): tests for the sequential per-batch
discovery loop's failure-isolation behavior. The batch loop itself lives
inline in run_scan.py's discovery block (not extracted to a standalone
function), so these tests exercise the loop's exact shape directly —
mirroring run_scan.py's discovery-block code (batch via _chunked +
_expand_and_dedup_hosts, try/except RuntimeError around the per-batch call,
continue on failure) — per RESEARCH.md's guidance to test the failure-
isolation behavior against a fake failing callable when a full main() run is
too heavy to construct in a unit test.
"""
from __future__ import annotations

from typing import List

import pytest

from quirk.models import CryptoEndpoint
from quirk.scanner.target_expander import _chunked, _expand_and_dedup_hosts, _MAX_HOSTS_PER_CIDR


def _run_batched_discovery(host_tokens: List[str], discover_fn, chunk_size: int = _MAX_HOSTS_PER_CIDR):
    """Mirrors run_scan.py's discovery-block batch loop exactly (Phase 144 / D-03/D-04):
    per-batch try/except RuntimeError, continue on failure, merge all successful
    batches' results. Returns (all_results, error_endpoints, batch_count).
    """
    error_endpoints: List[CryptoEndpoint] = []
    all_open_ports: List = []
    batch_num = 0
    host_iter = _expand_and_dedup_hosts(host_tokens)
    for batch in _chunked(host_iter, chunk_size):
        batch_num += 1
        try:
            batch_open_ports = discover_fn(batch)
            all_open_ports.extend(batch_open_ports)
        except RuntimeError as exc:
            error_endpoints.append(CryptoEndpoint(
                host=f"discovery-batch-{batch_num}",
                port=0,
                protocol="ERROR",
                scan_error=str(exc) or exc.__class__.__name__,
                scan_error_category="exception",
            ))
            continue
    return all_open_ports, error_endpoints, batch_num


def test_batch_failure_does_not_stop_subsequent_batches():
    """A batch that raises RuntimeError does not abort the loop — batch 2
    failing must not prevent batch 3 from running (DISC-02)."""
    calls = []

    def fake_discover(batch):
        calls.append(batch)
        if len(calls) == 2:
            raise RuntimeError("nmap discovery timed out — batch 2 sentinel")
        return [f"open:{batch[0]}"]

    # 3 single-host tokens, chunk_size=1 -> 3 batches.
    results, errors, batch_count = _run_batched_discovery(
        ["10.0.0.1", "10.0.0.2", "10.0.0.3"], fake_discover, chunk_size=1,
    )

    assert batch_count == 3, "all 3 batches must be attempted, not just up to the failure"
    assert len(calls) == 3, "batch 3's discover call must still happen after batch 2 fails"
    assert len(errors) == 1
    assert errors[0].scan_error_category == "exception"
    assert errors[0].protocol == "ERROR"


def test_batch_failure_merged_results_contain_successful_batches_only():
    """The merged open-ports result contains batch 1's and batch 3's ports;
    batch 2's hosts are simply absent (no crash)."""
    def fake_discover(batch):
        if batch == ["10.0.0.2"]:
            raise RuntimeError("simulated batch failure")
        return [f"open:{batch[0]}"]

    results, errors, batch_count = _run_batched_discovery(
        ["10.0.0.1", "10.0.0.2", "10.0.0.3"], fake_discover, chunk_size=1,
    )

    assert results == ["open:10.0.0.1", "open:10.0.0.3"]
    assert len(errors) == 1


def test_batch_loop_only_catches_runtime_error():
    """Catch RuntimeError only — not a bare Exception (matches
    run_nmap_discovery()'s three failure modes, all normalized to
    RuntimeError). A non-RuntimeError exception must still propagate."""
    def fake_discover(batch):
        raise ValueError("not a RuntimeError — should propagate, not be caught")

    with pytest.raises(ValueError):
        _run_batched_discovery(["10.0.0.1"], fake_discover, chunk_size=1)


def test_multi_batch_cidr_produces_more_than_one_batch():
    """A multi-address CIDR spanning >1 chunk-size produces more than one
    batch (real host expansion, not one raw-token batch — Pitfall 4)."""
    def fake_discover(batch):
        return [f"open:{h}" for h in batch]

    # /24 has 254 usable hosts; chunk_size=100 -> 3 batches (100, 100, 54).
    results, errors, batch_count = _run_batched_discovery(
        ["10.0.0.0/24"], fake_discover, chunk_size=100,
    )

    assert batch_count == 3
    assert errors == []
    assert len(results) == 254


def test_default_args_includes_max_parallelism():
    """_default_nmap_args must include '--max-parallelism' followed by '100' (D-07)."""
    from quirk.discovery.nmap_provider import _default_nmap_args

    args = _default_nmap_args("443,8443")
    # Must contain the flag and value as consecutive elements.
    assert "--max-parallelism" in args, (
        "--max-parallelism flag missing from default nmap args"
    )
    idx = args.index("--max-parallelism")
    assert args[idx + 1] == "100", (
        f"Expected '100' after --max-parallelism, got {args[idx + 1]!r}"
    )
