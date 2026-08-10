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

Phase 145 / Plan 01 (DISC-03): tests for the `-sn -PS<ports>` liveness
pre-pass arg builder, port-spec resolution (including the `--top-ports`
Pitfall-1 full-range fallback), and the allowlist gate on the assembled
`-PS<spec>` token before subprocess invocation.
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


# ---------------------------------------------------------------------------
# Phase 144 / Plan 02, Task 2 (D-04): discovery-stage ScanCheckpoint row shape
# ---------------------------------------------------------------------------

def _write_discovery_checkpoint(tmp_path, discovery_pf):
    """Mirrors run_scan.py's discovery-stage checkpoint write exactly."""
    from quirk.db import init_db
    from quirk.cli.job_progress import write_scan_checkpoint

    db_path = str(tmp_path / "checkpoint_test.db")
    init_db(db_path)
    write_scan_checkpoint(
        db_path, "scan-run-1", "discovery",
        status="partial" if discovery_pf else "completed",
        endpoint_count=3, partial_failure=bool(discovery_pf),
        error_summary=discovery_pf or None,
    )
    return db_path


def test_discovery_checkpoint_partial_on_batch_failure(tmp_path):
    """After a discovery run where at least one batch failed, a
    ScanCheckpoint row exists with stage='discovery' and status='partial'."""
    from quirk.db import get_session
    from quirk.models import ScanCheckpoint

    fake_pf = [{"stage": "discovery", "scanner": "discovery-batch-2",
                "error_category": "exception", "error_message": "boom", "endpoint_count": 0}]
    db_path = _write_discovery_checkpoint(tmp_path, fake_pf)

    with get_session(db_path) as db:
        row = db.query(ScanCheckpoint).filter_by(scan_run_id="scan-run-1", stage="discovery").one()
        assert row.status == "partial"
        assert row.partial_failure is True


def test_discovery_checkpoint_completed_when_all_batches_succeed(tmp_path):
    """After a discovery run where all batches succeeded, the stage='discovery'
    row has status='completed'."""
    from quirk.db import get_session
    from quirk.models import ScanCheckpoint

    db_path = _write_discovery_checkpoint(tmp_path, [])

    with get_session(db_path) as db:
        row = db.query(ScanCheckpoint).filter_by(scan_run_id="scan-run-1", stage="discovery").one()
        assert row.status == "completed"
        assert row.partial_failure is False


def test_discovery_checkpoint_pf_derived_from_collect_stage_partial_failures():
    """_collect_stage_partial_failures("discovery", ...) correctly derives the
    partial-failure list from new error_endpoints appended during the batch
    loop, matching the exact pattern run_scan.py uses for every other stage."""
    import sys
    sys.path.insert(0, ".") if "." not in sys.path else None
    from run_scan import _collect_stage_partial_failures

    error_endpoints: List[CryptoEndpoint] = []
    err_before = len(error_endpoints)

    def fake_discover(batch):
        if batch == ["10.0.0.2"]:
            raise RuntimeError("simulated batch failure")
        return [f"open:{batch[0]}"]

    def _loop():
        for batch in _chunked(_expand_and_dedup_hosts(["10.0.0.1", "10.0.0.2", "10.0.0.3"]), 1):
            try:
                fake_discover(batch)
            except RuntimeError as exc:
                error_endpoints.append(CryptoEndpoint(
                    host="discovery-batch-x", port=0, protocol="ERROR",
                    scan_error=str(exc), scan_error_category="exception",
                ))
                continue

    run_stats: dict = {}
    _loop()
    discovery_pf = _collect_stage_partial_failures(run_stats, "discovery", error_endpoints, err_before)

    assert len(discovery_pf) == 1
    assert discovery_pf[0]["stage"] == "discovery"
    assert run_stats["partial_failures"] == discovery_pf


def test_models_scancheckpoint_docstring_documents_discovery_stage():
    """quirk/models.py's ScanCheckpoint docstring must list 'discovery' among
    stage values (doc-only, no schema change)."""
    import inspect
    from quirk.models import ScanCheckpoint

    assert "discovery" in inspect.getdoc(ScanCheckpoint)


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


# ---------------------------------------------------------------------------
# Phase 145 / Plan 01 (DISC-03): liveness pre-pass arg/port-spec builders
# ---------------------------------------------------------------------------

def test_liveness_args_use_sn_and_ps():
    from quirk.discovery.nmap_provider import _liveness_nmap_args

    args = _liveness_nmap_args("443,8443")

    assert args[0] == "-sn"
    assert "-PS443,8443" in args
    assert "-sT" not in args
    assert "-Pn" not in args
    assert "--open" not in args


def test_liveness_args_carry_retry_and_parallelism_defaults():
    from quirk.discovery.nmap_provider import _liveness_nmap_args

    args = _liveness_nmap_args("443")

    for flag, value in (
        ("--max-retries", "1"),
        ("--host-timeout", "10s"),
        ("--max-parallelism", "100"),
    ):
        assert flag in args, f"{flag} missing from liveness args"
        idx = args.index(flag)
        assert args[idx + 1] == value, f"Expected {value!r} after {flag}, got {args[idx + 1]!r}"


def test_liveness_port_spec_matches_sweep_ports():
    from quirk.discovery.nmap_provider import _resolve_liveness_port_spec

    assert _resolve_liveness_port_spec([443, 22, 443], None) == "22,443"


def test_liveness_port_spec_resolves_full_range_for_wide_scopes():
    from quirk.discovery.nmap_provider import (
        _resolve_liveness_port_spec,
        default_nmap_ports_csv,
    )

    assert _resolve_liveness_port_spec([], None) == default_nmap_ports_csv(
        (443, 8443, 9443, 10443, 5001)
    )
    assert _resolve_liveness_port_spec([], "-p-") == "-"
    assert _resolve_liveness_port_spec([], "--top-ports 1000") == "-"


def test_liveness_check_empty_targets_returns_empty():
    from quirk.discovery.nmap_provider import run_nmap_liveness_check

    result = run_nmap_liveness_check(targets=[], ports=[443], output_dir="/tmp/does-not-matter")

    assert result == []


def test_liveness_port_spec_validated(tmp_path):
    from quirk.discovery.nmap_provider import run_nmap_liveness_check

    with pytest.raises(ValueError):
        run_nmap_liveness_check(
            targets=["10.0.0.1"],
            ports=[],
            output_dir=str(tmp_path),
            port_spec_override="443;rm",
        )


def _write_fake_liveness_xml(args: List[str], body: str) -> None:
    xml_path = args[args.index("-oX") + 1]
    with open(xml_path, "w") as f:
        f.write(f'<?xml version="1.0"?><nmaprun>{body}</nmaprun>')


class _FakeCompletedProcess:
    returncode = 0
    stdout = ""
    stderr = ""


def test_liveness_synthesizes_down_hosts_when_runstats_trustworthy(tmp_path, monkeypatch):
    """Bugfix regression (Phase 145 D-06 human-UAT, 2026-08-10): a real -sn -PS
    subnet sweep only emits a <host> element for up hosts. Down hosts must be
    inferred from <runstats><hosts total up down/> when it fully accounts for
    every target, otherwise run_scan.py's batch filter never skips anyone."""
    from quirk.discovery import nmap_provider

    targets = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def _fake_run(args, **kwargs):
        _write_fake_liveness_xml(
            args,
            '<host><status state="up" reason="syn-ack"/>'
            '<address addr="10.0.0.1" addrtype="ipv4"/></host>'
            '<runstats><finished exit="success"/>'
            '<hosts up="1" down="2" total="3"/></runstats>',
        )
        return _FakeCompletedProcess()

    monkeypatch.setattr(nmap_provider.subprocess, "run", _fake_run)

    result = nmap_provider.run_nmap_liveness_check(targets=targets, ports=[443], output_dir=str(tmp_path))

    by_host = {r.host: r for r in result}
    assert by_host["10.0.0.1"].up is True
    assert by_host["10.0.0.2"].up is False
    assert by_host["10.0.0.2"].reason == "no-response (inferred from runstats)"
    assert by_host["10.0.0.3"].up is False


# ---------------------------------------------------------------------------
# Phase 146 / Plan 02 (DISC-05/DISC-06): batch-size-scaled timeout + timing
# template helpers.
# ---------------------------------------------------------------------------

def test_discovery_timeout_for_batch_boundaries():
    from quirk.discovery.nmap_provider import discovery_timeout_for_batch

    values = {size: discovery_timeout_for_batch(size) for size in (0, 1, 256, 257, 1024, 5000)}

    assert values[1] < 60, "a 1-host batch must get a timeout well under 300s"
    assert values[1024] <= 300, "a full 1024-host batch must not exceed the pre-existing 300s ceiling"
    assert values[5000] == 300, "an oversized batch must clamp to exactly the 300s ceiling"

    sizes_in_order = (0, 1, 256, 257, 1024, 5000)
    ordered_values = [values[s] for s in sizes_in_order]
    assert ordered_values == sorted(ordered_values), "timeout must be monotonically non-decreasing"


def test_discovery_timeout_for_batch_degrades_on_bad_input():
    from quirk.discovery.nmap_provider import discovery_timeout_for_batch, _DISCOVERY_TIMEOUT_BASE_SECONDS

    assert discovery_timeout_for_batch("not-an-int") == _DISCOVERY_TIMEOUT_BASE_SECONDS
    assert discovery_timeout_for_batch(-5) == _DISCOVERY_TIMEOUT_BASE_SECONDS
    assert discovery_timeout_for_batch(0) == _DISCOVERY_TIMEOUT_BASE_SECONDS


def test_discovery_timing_template_for_batch_flips_at_256_257():
    from quirk.discovery.nmap_provider import discovery_timing_template_for_batch

    assert discovery_timing_template_for_batch(1) == "-T4"
    assert discovery_timing_template_for_batch(256) == "-T4"
    assert discovery_timing_template_for_batch(257) == "-T3"
    assert discovery_timing_template_for_batch(1024) == "-T3"


def test_discovery_timing_template_for_batch_matches_safe_arg_re():
    from quirk.discovery.nmap_provider import discovery_timing_template_for_batch, _SAFE_NMAP_ARG_RE

    assert _SAFE_NMAP_ARG_RE.fullmatch(discovery_timing_template_for_batch(1))
    assert _SAFE_NMAP_ARG_RE.fullmatch(discovery_timing_template_for_batch(1024))


def test_liveness_does_not_synthesize_down_hosts_when_runstats_untrustworthy(tmp_path, monkeypatch):
    """When <runstats> total doesn't reconcile with the batch (e.g. truncated
    output), do NOT infer down hosts — fail open exactly like a RuntimeError,
    so run_scan.py's batch filter sweeps every host in the batch."""
    from quirk.discovery import nmap_provider

    targets = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def _fake_run(args, **kwargs):
        _write_fake_liveness_xml(
            args,
            '<host><status state="up" reason="syn-ack"/>'
            '<address addr="10.0.0.1" addrtype="ipv4"/></host>'
            '<runstats><finished exit="success"/>'
            '<hosts up="1" down="0" total="1"/></runstats>',
        )
        return _FakeCompletedProcess()

    monkeypatch.setattr(nmap_provider.subprocess, "run", _fake_run)

    result = nmap_provider.run_nmap_liveness_check(targets=targets, ports=[443], output_dir=str(tmp_path))

    assert len(result) == 1
    assert result[0].host == "10.0.0.1"
    assert result[0].up is True
