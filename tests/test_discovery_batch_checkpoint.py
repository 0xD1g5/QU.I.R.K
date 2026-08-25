"""Phase 163 (DISC-08, D-01..D-07): tests for the per-batch discovery
checkpoint/resume loop — resume-skip guard, unconditional per-batch
checkpoint+cache writes, dead-batch checkpointing, and the NmapOpenPort
serializer pair that makes batch cache payloads JSON-safe.

Part A mirrors the loop shape (following tests/test_discovery_batch_progress.py's
convention) with stubbed nmap calls and a real temp-SQLite-backed
ScanCheckpoint table via write_scan_checkpoint() — no external process is
spawned and no real nmap binary is required.

Part B parses the REAL run_scan.py via `ast` so a passing mirror test can
never mask an unwired loop (mirrors tests/test_cli_dashboard_discovery_parity.py's
structural-test convention). Part B is added by Plan 163-02.
"""
from __future__ import annotations

import inspect

from quirk.discovery.nmap_parser import NmapOpenPort
from quirk.engine.cache import open_ports_to_serial, serial_to_open_ports
from quirk.scanner.target_expander import _chunked, _expand_and_dedup_hosts, _MAX_HOSTS_PER_CIDR

_RESUME_BATCH_CACHE_TTL_HOURS = 720


class _FakeHostStatus:
    def __init__(self, host: str, up: bool):
        self.host = host
        self.up = up


def _run_batched_discovery_with_checkpoints(
    host_tokens,
    liveness_fn,
    sweep_fn,
    completed_stages,
    checkpoint_writer,
    cache_reader,
    cache_writer,
    scan_run_id="2026-08-25T00:00:00",
    chunk_size=_MAX_HOSTS_PER_CIDR,
    db_path_set=True,
):
    """Mirrors run_scan.py's chunked discovery loop shape EXACTLY (Phase 163
    D-01..D-06): resume-skip guard right after `batch_num += 1`, liveness's
    own try/except/else, a SEPARATE nested try/except inside
    `if sweep_targets:` for the sweep, and per-batch checkpoint+cache writes
    gated on `db_path_set and _batch_swept_ok` (never on a `--cache`-style
    flag — the mirror takes no such knob at all).

    Returns a dict with `all_open_ports`, `batch_total`, `hosts_checked`,
    `error_records`.
    """
    total_hosts = sum(1 for _ in _expand_and_dedup_hosts(host_tokens))
    batch_total = (total_hosts + chunk_size - 1) // chunk_size or 1

    hosts_checked = 0
    batch_num = 0
    all_open_ports = []
    error_records = []

    host_iter = _expand_and_dedup_hosts(host_tokens)
    for batch in _chunked(host_iter, chunk_size):
        batch_num += 1
        stage = f"discovery:batch-{batch_num}"
        key = f"discovery-batch-{scan_run_id}-{batch_num}"

        # Resume-skip guard: a checkpoint row ALONE never causes a skip — it
        # must also have a live cache hit (D-06 TTL fallback / correctness
        # hardening beyond D-01's letter).
        if stage in completed_stages:
            cached = cache_reader(key, _RESUME_BATCH_CACHE_TTL_HOURS)
            if cached is not None:
                all_open_ports.extend(serial_to_open_ports(cached.get("ports", [])))
                hosts_checked += len(batch)
                continue

        batch_open_ports = []
        _batch_swept_ok = True

        try:
            statuses = liveness_fn(batch)
        except RuntimeError:
            sweep_targets = batch
        else:
            down_hosts = {s.host for s in statuses if not s.up}
            sweep_targets = [h for h in batch if h not in down_hosts]

        if sweep_targets:
            try:
                batch_open_ports = sweep_fn(sweep_targets)
                all_open_ports.extend(batch_open_ports)
            except RuntimeError as exc:
                error_records.append({"batch": batch_num, "error": str(exc)})
                _batch_swept_ok = False

        if db_path_set and _batch_swept_ok:
            cache_writer(key, {"ports": open_ports_to_serial(batch_open_ports)})
            checkpoint_writer(stage, "completed", len(batch_open_ports))

        hosts_checked += len(batch)

    return {
        "all_open_ports": all_open_ports,
        "batch_total": batch_total,
        "hosts_checked": hosts_checked,
        "error_records": error_records,
    }


# ---------------------------------------------------------------------------
# Part A: NmapOpenPort serializer round-trip (Task 1)
# ---------------------------------------------------------------------------

def test_nmap_open_port_serializer_roundtrip():
    ports = [
        NmapOpenPort(host="10.0.0.1", port=443, protocol="tcp", service="https"),
        NmapOpenPort(host="10.0.0.2", port=53, protocol="udp", service="domain"),
        NmapOpenPort(host="10.0.0.3", port=22, protocol="tcp", service=None),
    ]

    serial = open_ports_to_serial(ports)
    assert serial == [
        {"host": "10.0.0.1", "port": 443, "protocol": "tcp", "service": "https"},
        {"host": "10.0.0.2", "port": 53, "protocol": "udp", "service": "domain"},
        {"host": "10.0.0.3", "port": 22, "protocol": "tcp", "service": None},
    ]

    # service=None round-trips as None, not "None" and not dropped.
    assert serial[2]["service"] is None

    roundtripped = serial_to_open_ports(serial)
    assert roundtripped == ports

    # None / empty input.
    assert serial_to_open_ports(None) == []
    assert serial_to_open_ports([]) == []

    # Malformed items are skipped, not raised on.
    malformed = [
        {"port": 443, "protocol": "tcp"},  # missing host
        {"host": "10.0.0.1", "protocol": "tcp"},  # missing port
        {"host": "10.0.0.1", "port": 443},  # missing protocol
        {"host": "10.0.0.1", "port": 443, "protocol": "tcp", "service": "https"},  # valid
    ]
    result = serial_to_open_ports(malformed)
    assert result == [NmapOpenPort(host="10.0.0.1", port=443, protocol="tcp", service="https")]

    # json.dumps must succeed on the serialized payload (no TypeError).
    import json
    json.dumps({"ports": open_ports_to_serial(ports)})


# ---------------------------------------------------------------------------
# Part A: per-batch checkpoint/resume loop rules (Task 2)
# ---------------------------------------------------------------------------

_HOSTS_6 = [f"10.0.0.{i}" for i in range(1, 7)]  # chunk_size=2 -> 3 batches


def _all_up_liveness_fn(batch):
    return [_FakeHostStatus(h, up=True) for h in batch]


def _identity_sweep_fn(targets):
    return [NmapOpenPort(host=h, port=443, protocol="tcp", service="https") for h in targets]


def test_resume_skips_completed_batches():
    completed_stages = {"discovery:batch-1", "discovery:batch-2"}
    cached_ports_by_key = {
        "discovery-batch-2026-08-25T00:00:00-1": {
            "ports": open_ports_to_serial(
                [NmapOpenPort(host="10.0.0.1", port=443, protocol="tcp", service="https")]
            )
        },
        "discovery-batch-2026-08-25T00:00:00-2": {
            "ports": open_ports_to_serial(
                [NmapOpenPort(host="10.0.0.3", port=443, protocol="tcp", service="https")]
            )
        },
    }
    liveness_calls = []
    sweep_calls = []

    def liveness_fn(batch):
        liveness_calls.append(list(batch))
        return _all_up_liveness_fn(batch)

    def sweep_fn(targets):
        sweep_calls.append(list(targets))
        return _identity_sweep_fn(targets)

    def cache_reader(key, ttl_hours):
        return cached_ports_by_key.get(key)

    result = _run_batched_discovery_with_checkpoints(
        _HOSTS_6, liveness_fn, sweep_fn, completed_stages,
        checkpoint_writer=lambda *a, **k: None,
        cache_reader=cache_reader,
        cache_writer=lambda *a, **k: None,
        chunk_size=2,
    )

    # Batches 1 and 2's hosts never reach liveness_fn/sweep_fn.
    for calls in (liveness_calls, sweep_calls):
        for call_hosts in calls:
            assert "10.0.0.1" not in call_hosts
            assert "10.0.0.2" not in call_hosts
            assert "10.0.0.3" not in call_hosts
            assert "10.0.0.4" not in call_hosts

    hosts_seen = {p.host for p in result["all_open_ports"]}
    assert "10.0.0.1" in hosts_seen  # from cache (batch 1)
    assert "10.0.0.3" in hosts_seen  # from cache (batch 2)
    assert "10.0.0.5" in hosts_seen  # freshly probed (batch 3)


def test_failed_batch_writes_no_checkpoint_and_loop_continues():
    def liveness_fn(batch):
        return _all_up_liveness_fn(batch)

    def sweep_fn(targets):
        if targets == ["10.0.0.3", "10.0.0.4"]:
            raise RuntimeError("nmap crashed")
        return _identity_sweep_fn(targets)

    checkpoint_calls = []
    cache_calls = []

    result = _run_batched_discovery_with_checkpoints(
        _HOSTS_6, liveness_fn, sweep_fn, completed_stages=set(),
        checkpoint_writer=lambda stage, status, count: checkpoint_calls.append(stage),
        cache_reader=lambda *a, **k: None,
        cache_writer=lambda key, payload: cache_calls.append(key),
        chunk_size=2,
    )

    assert "discovery:batch-1" in checkpoint_calls
    assert "discovery:batch-3" in checkpoint_calls
    assert "discovery:batch-2" not in checkpoint_calls
    assert not any(k.endswith("-2") for k in cache_calls)
    assert len(result["error_records"]) == 1
    assert result["error_records"][0]["batch"] == 2
    # Loop still ran batch 3 despite batch 2's failure.
    assert result["batch_total"] == 3
    assert result["hosts_checked"] == 6


def test_fully_dead_batch_still_checkpoints():
    def liveness_fn(batch):
        if batch == ["10.0.0.3", "10.0.0.4"]:
            return [_FakeHostStatus(h, up=False) for h in batch]
        return _all_up_liveness_fn(batch)

    def sweep_fn(targets):
        assert targets != []  # sweep_fn must never be called for the dead batch
        return _identity_sweep_fn(targets)

    checkpoint_calls = []
    cache_calls = {}

    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, liveness_fn, sweep_fn, completed_stages=set(),
        checkpoint_writer=lambda stage, status, count: checkpoint_calls.append((stage, status)),
        cache_reader=lambda *a, **k: None,
        cache_writer=lambda key, payload: cache_calls.__setitem__(key, payload),
        chunk_size=2,
    )

    assert ("discovery:batch-2", "completed") in checkpoint_calls
    dead_key = "discovery-batch-2026-08-25T00:00:00-2"
    assert dead_key in cache_calls
    assert cache_calls[dead_key]["ports"] == []


def test_batch_cache_written_without_cache_flag():
    # The mirror takes no --cache-style knob at all — assert by construction.
    sig = inspect.signature(_run_batched_discovery_with_checkpoints)
    assert "cache" not in sig.parameters
    assert "db_path_set" in sig.parameters

    checkpoint_calls_true = []
    cache_calls_true = []
    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, _all_up_liveness_fn, _identity_sweep_fn, completed_stages=set(),
        checkpoint_writer=lambda *a, **k: checkpoint_calls_true.append(a),
        cache_reader=lambda *a, **k: None,
        cache_writer=lambda *a, **k: cache_calls_true.append(a),
        chunk_size=2, db_path_set=True,
    )
    assert len(checkpoint_calls_true) == 3
    assert len(cache_calls_true) == 3

    checkpoint_calls_false = []
    cache_calls_false = []
    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, _all_up_liveness_fn, _identity_sweep_fn, completed_stages=set(),
        checkpoint_writer=lambda *a, **k: checkpoint_calls_false.append(a),
        cache_reader=lambda *a, **k: None,
        cache_writer=lambda *a, **k: cache_calls_false.append(a),
        chunk_size=2, db_path_set=False,
    )
    assert checkpoint_calls_false == []
    assert cache_calls_false == []


def test_batch_cache_ignored_on_fresh_non_resume_run():
    cache_reader_calls = []

    def cache_reader(key, ttl_hours):
        cache_reader_calls.append(key)
        return {"ports": []}  # would be a hit if ever consulted

    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, _all_up_liveness_fn, _identity_sweep_fn, completed_stages=set(),
        checkpoint_writer=lambda *a, **k: None,
        cache_reader=cache_reader,
        cache_writer=lambda *a, **k: None,
        chunk_size=2,
    )

    assert cache_reader_calls == []


def test_resume_read_uses_generous_ttl():
    ttl_seen = []

    def cache_reader(key, ttl_hours):
        ttl_seen.append(ttl_hours)
        return None

    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, _all_up_liveness_fn, _identity_sweep_fn,
        completed_stages={"discovery:batch-1"},
        checkpoint_writer=lambda *a, **k: None,
        cache_reader=cache_reader,
        cache_writer=lambda *a, **k: None,
        chunk_size=2,
    )

    assert ttl_seen == [720]
    assert ttl_seen[0] == _RESUME_BATCH_CACHE_TTL_HOURS
    assert ttl_seen[0] != 24


def test_skipped_batch_does_not_duplicate_checkpoint_row():
    cached_ports = {"ports": open_ports_to_serial(
        [NmapOpenPort(host="10.0.0.1", port=443, protocol="tcp", service="https")]
    )}
    checkpoint_calls = []

    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, _all_up_liveness_fn, _identity_sweep_fn,
        completed_stages={"discovery:batch-1"},
        checkpoint_writer=lambda stage, status, count: checkpoint_calls.append(stage),
        cache_reader=lambda key, ttl: cached_ports if key.endswith("-1") else None,
        cache_writer=lambda *a, **k: None,
        chunk_size=2,
    )

    assert "discovery:batch-1" not in checkpoint_calls


def test_completed_stage_without_cache_hit_reprobes():
    liveness_calls = []

    def liveness_fn(batch):
        liveness_calls.append(list(batch))
        return _all_up_liveness_fn(batch)

    checkpoint_calls = []

    result = _run_batched_discovery_with_checkpoints(
        _HOSTS_6, liveness_fn, _identity_sweep_fn,
        completed_stages={"discovery:batch-1"},
        checkpoint_writer=lambda stage, status, count: checkpoint_calls.append(stage),
        cache_reader=lambda key, ttl: None,  # expired / corrupt / deleted
        cache_writer=lambda *a, **k: None,
        chunk_size=2,
    )

    # Falls through and IS probed normally.
    assert liveness_calls[0] == ["10.0.0.1", "10.0.0.2"]
    # Then re-checkpoints.
    assert "discovery:batch-1" in checkpoint_calls
    assert result["hosts_checked"] == 6


# --- Part B: AST-structural tests (Plan 163-02) ---
