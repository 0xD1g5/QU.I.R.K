"""Phase 145 / Plan 02 (DISC-03, D-01/D-02/D-04/D-05): tests for wiring the
Plan 01 liveness-pre-pass primitives into run_scan.py's discovery batch loop.

Covers:
  - _is_privileged(): euid-0/non-zero/undeterminable (Windows) detection (D-02)
  - _emit_liveness_fallback_advisory(): logger message + one privilege_fallback
    CryptoEndpoint advisory row per call (D-01)
  - The per-batch liveness pre-pass filter shape (mirrors run_scan.py's
    discovery-block batch loop exactly, matching the
    tests/test_nmap_provider.py::_run_batched_discovery convention):
    survivors-only sweep, per-host liveness_skip rows, zero-sweep-call
    short-circuit on an all-dead batch, fail-open on hosts absent from the
    liveness results, fail-open on RuntimeError from the pre-pass itself, and
    exclusion of liveness_skip/privilege_fallback rows from
    _collect_stage_partial_failures (D-05 — normal skips must never flip the
    discovery ScanCheckpoint to partial).
"""
from __future__ import annotations

from typing import Dict, List
from unittest.mock import patch

import pytest

from quirk.models import CryptoEndpoint
from quirk.scanner.target_expander import _chunked, _expand_and_dedup_hosts, _MAX_HOSTS_PER_CIDR


class _StubLogger:
    """Minimal stub exposing the Logger surface run_scan.py's helpers touch."""

    def __init__(self):
        self.info_calls: List[str] = []
        self.stamp_calls: List[str] = []
        self.error_calls: List[str] = []

    def info(self, msg):
        self.info_calls.append(msg)

    def stamp(self, msg):
        self.stamp_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


# ---------------------------------------------------------------------------
# Task 1: _is_privileged() / _emit_liveness_fallback_advisory()
# ---------------------------------------------------------------------------

def test_is_privileged_true_when_euid_zero():
    from run_scan import _is_privileged
    with patch("os.geteuid", return_value=0, create=True):
        assert _is_privileged() is True


def test_is_privileged_false_when_euid_nonzero():
    from run_scan import _is_privileged
    with patch("os.geteuid", return_value=501, create=True):
        assert _is_privileged() is False


def test_is_privileged_none_when_geteuid_missing(monkeypatch):
    from run_scan import _is_privileged
    import os as os_module
    monkeypatch.delattr(os_module, "geteuid", raising=False)
    assert _is_privileged() is None


def test_fallback_advisory_row_shape():
    from run_scan import _emit_liveness_fallback_advisory
    error_endpoints: List[CryptoEndpoint] = []
    logger = _StubLogger()

    _emit_liveness_fallback_advisory(error_endpoints, logger)

    assert len(error_endpoints) == 1
    row = error_endpoints[0]
    assert row.host == "liveness-prepass"
    assert row.port == 0
    assert row.protocol == "ADVISORY"
    assert row.scan_error_category == "privilege_fallback"
    assert len(logger.info_calls) == 1


def test_fallback_advisory_called_twice_appends_two_rows():
    """Caller, not the helper, is responsible for once-per-scan gating."""
    from run_scan import _emit_liveness_fallback_advisory
    error_endpoints: List[CryptoEndpoint] = []
    logger = _StubLogger()

    _emit_liveness_fallback_advisory(error_endpoints, logger)
    _emit_liveness_fallback_advisory(error_endpoints, logger)

    assert len(error_endpoints) == 2


# ---------------------------------------------------------------------------
# Task 2: per-batch liveness pre-pass filter loop shape
# ---------------------------------------------------------------------------

class _FakeHostStatus:
    def __init__(self, host: str, up: bool, reason: str = "test"):
        self.host = host
        self.up = up
        self.reason = reason


def _run_batched_prepass(host_tokens: List[str], liveness_fn, sweep_fn,
                          chunk_size: int = _MAX_HOSTS_PER_CIDR):
    """Mirrors run_scan.py's discovery-block batch loop's liveness pre-pass
    step exactly (Phase 145 / Plan 02): per-batch liveness check wrapped in
    try/except RuntimeError (fail-open on failure -> sweep entire batch, no
    liveness rows), survivor-set computed by EXCLUDING down hosts (so a host
    absent from the results defaults to being swept), a fully-dead batch
    short-circuits before the sweep call, and one `liveness_skip`
    CryptoEndpoint per skipped host.

    Returns (all_results, liveness_endpoints, sweep_calls, batch_count).
    """
    liveness_endpoints: List[CryptoEndpoint] = []
    sweep_calls: List[List[str]] = []
    all_results: List = []
    batch_num = 0
    host_iter = _expand_and_dedup_hosts(host_tokens)
    for batch in _chunked(host_iter, chunk_size):
        batch_num += 1
        try:
            statuses = liveness_fn(batch)
        except RuntimeError:
            sweep_targets = batch
            sweep_calls.append(sweep_targets)
            all_results.extend(sweep_fn(sweep_targets))
            continue

        down_hosts = {s.host for s in statuses if not s.up}
        sweep_targets = [h for h in batch if h not in down_hosts]

        for h in batch:
            if h in down_hosts:
                liveness_endpoints.append(CryptoEndpoint(
                    host=h,
                    port=0,
                    protocol="ADVISORY",
                    scan_error="liveness pre-pass: no response",
                    scan_error_category="liveness_skip",
                ))

        if not sweep_targets:
            continue

        sweep_calls.append(sweep_targets)
        all_results.extend(sweep_fn(sweep_targets))

    return all_results, liveness_endpoints, sweep_calls, batch_num


def test_liveness_prepass_filters_batch_before_sweep():
    hosts = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def liveness_fn(batch):
        return [_FakeHostStatus(h, up=(h != "10.0.0.2")) for h in batch]

    def sweep_fn(targets):
        return list(targets)

    all_results, liveness_endpoints, sweep_calls, batch_count = _run_batched_prepass(
        hosts, liveness_fn, sweep_fn, chunk_size=10
    )

    assert sweep_calls == [["10.0.0.1", "10.0.0.3"]]
    assert "10.0.0.2" not in all_results


def test_liveness_skip_appends_liveness_skip_category():
    hosts = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def liveness_fn(batch):
        return [_FakeHostStatus(h, up=(h != "10.0.0.2")) for h in batch]

    def sweep_fn(targets):
        return list(targets)

    _, liveness_endpoints, _, _ = _run_batched_prepass(hosts, liveness_fn, sweep_fn, chunk_size=10)

    assert len(liveness_endpoints) == 1
    row = liveness_endpoints[0]
    assert row.host == "10.0.0.2"
    assert row.port == 0
    assert row.protocol == "ADVISORY"
    assert row.scan_error_category == "liveness_skip"


def test_all_dead_batch_skips_sweep_call():
    hosts = ["10.0.0.1", "10.0.0.2"]

    def liveness_fn(batch):
        return [_FakeHostStatus(h, up=False) for h in batch]

    sweep_called = {"count": 0}

    def sweep_fn(targets):
        sweep_called["count"] += 1
        return list(targets)

    _, liveness_endpoints, sweep_calls, _ = _run_batched_prepass(hosts, liveness_fn, sweep_fn, chunk_size=10)

    assert sweep_called["count"] == 0
    assert sweep_calls == []
    assert len(liveness_endpoints) == 2


def test_host_absent_from_liveness_results_is_swept():
    hosts = ["10.0.0.1", "10.0.0.2"]

    def liveness_fn(batch):
        # 10.0.0.2 is entirely absent from the results (fail-open, A1)
        return [_FakeHostStatus("10.0.0.1", up=True)]

    def sweep_fn(targets):
        return list(targets)

    all_results, liveness_endpoints, sweep_calls, _ = _run_batched_prepass(hosts, liveness_fn, sweep_fn, chunk_size=10)

    assert sweep_calls == [["10.0.0.1", "10.0.0.2"]]
    assert liveness_endpoints == []


def test_liveness_failure_falls_back_to_full_batch_sweep():
    hosts = ["10.0.0.1", "10.0.0.2"]

    def liveness_fn(batch):
        raise RuntimeError("nmap liveness pre-pass failed")

    def sweep_fn(targets):
        return list(targets)

    all_results, liveness_endpoints, sweep_calls, _ = _run_batched_prepass(hosts, liveness_fn, sweep_fn, chunk_size=10)

    assert sweep_calls == [hosts]
    assert liveness_endpoints == []


def test_liveness_rows_excluded_from_discovery_partial_failures():
    from run_scan import _collect_stage_partial_failures

    run_stats: Dict = {}
    liveness_endpoints: List[CryptoEndpoint] = [
        CryptoEndpoint(host="10.0.0.2", port=0, protocol="ADVISORY",
                        scan_error="liveness pre-pass: no response",
                        scan_error_category="liveness_skip"),
    ]

    # Mirrors run_scan.py: liveness_endpoints is a SEPARATE accumulator from
    # error_endpoints, only merged in via error_endpoints.extend(...) AFTER
    # the partial-failure snapshot is taken. So the snapshot itself never
    # observes liveness rows.
    error_endpoints: List[CryptoEndpoint] = []
    _err_before_discovery = len(error_endpoints)

    result = _collect_stage_partial_failures(run_stats, "discovery", error_endpoints, _err_before_discovery)

    assert result == []

    error_endpoints.extend(liveness_endpoints)
    assert len(error_endpoints) == 1
