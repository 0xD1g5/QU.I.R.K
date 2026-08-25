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

import ast
import inspect
from pathlib import Path

from sqlalchemy import create_engine

from quirk.cli.job_progress import write_scan_checkpoint
from quirk.discovery.nmap_parser import NmapOpenPort
from quirk.engine.cache import load_cache, open_ports_to_serial, save_cache, serial_to_open_ports
from quirk.models import Base, ScanCheckpoint
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


# ---------------------------------------------------------------------------
# Part A: real-SQLite two-invocation interruption simulation (Task 3)
# ---------------------------------------------------------------------------

def test_resume_skips_completed_batches_against_real_db(tmp_path):
    db_path = str(tmp_path / "scan.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    output_dir = str(tmp_path)
    scan_run_id = "2026-08-25T12:00:00"

    def checkpoint_writer(stage, status, count):
        write_scan_checkpoint(db_path, scan_run_id, stage, status, endpoint_count=count)

    def cache_writer(key, payload):
        save_cache(output_dir, key, payload)

    def cache_reader(key, ttl_hours):
        return load_cache(output_dir, key, ttl_hours)

    # Invocation 1: batch 3 fails (simulated interruption).
    def sweep_fn_invocation1(targets):
        if targets == ["10.0.0.5", "10.0.0.6"]:
            raise RuntimeError("interrupted")
        return _identity_sweep_fn(targets)

    _run_batched_discovery_with_checkpoints(
        _HOSTS_6, _all_up_liveness_fn, sweep_fn_invocation1, completed_stages=set(),
        checkpoint_writer=checkpoint_writer,
        cache_reader=cache_reader,
        cache_writer=cache_writer,
        scan_run_id=scan_run_id,
        chunk_size=2,
    )

    # Invocation 2: load completed_stages from the real DB, exactly as
    # run_scan.py's resume-load block does (run_scan.py:1493-1524).
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = (
            session.query(ScanCheckpoint)
            .filter(
                ScanCheckpoint.scan_run_id == scan_run_id,
                ScanCheckpoint.status.in_(["completed", "partial"]),
            )
            .all()
        )
        completed_stages = {r.stage for r in rows}
    finally:
        session.close()
        engine.dispose()

    assert completed_stages == {"discovery:batch-1", "discovery:batch-2"}

    liveness_calls = []
    sweep_calls = []

    def liveness_fn(batch):
        liveness_calls.append(list(batch))
        return _all_up_liveness_fn(batch)

    def sweep_fn_invocation2(targets):
        sweep_calls.append(list(targets))
        return _identity_sweep_fn(targets)

    result = _run_batched_discovery_with_checkpoints(
        _HOSTS_6, liveness_fn, sweep_fn_invocation2, completed_stages=completed_stages,
        checkpoint_writer=checkpoint_writer,
        cache_reader=cache_reader,
        cache_writer=cache_writer,
        scan_run_id=scan_run_id,
        chunk_size=2,
    )

    # (a) liveness/sweep are called ONLY for batch 3's hosts.
    assert liveness_calls == [["10.0.0.5", "10.0.0.6"]]
    assert sweep_calls == [["10.0.0.5", "10.0.0.6"]]

    # (b) all_open_ports is the union of batches 1, 2 (from cache) and 3
    # (freshly probed).
    hosts_seen = {p.host for p in result["all_open_ports"]}
    assert hosts_seen == {"10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4", "10.0.0.5", "10.0.0.6"}

    # (c) exactly 3 scan_checkpoints rows for this scan_run_id — batches 1
    # and 2 did not write duplicates on invocation 2.
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        row_count = (
            session.query(ScanCheckpoint)
            .filter(ScanCheckpoint.scan_run_id == scan_run_id)
            .count()
        )
    finally:
        session.close()
        engine.dispose()
    assert row_count == 3


def test_batch_stage_names_fit_the_stage_column():
    stage_column_length = ScanCheckpoint.__table__.columns["stage"].type.length
    assert len("discovery:batch-4294967296") <= stage_column_length


# --- Part B: AST-structural tests (Plan 163-02) ---
#
# These parse the REAL run_scan.py (not the Part A mirror helper above) so a
# passing mirror test can never mask an unwired real loop. Technique copied
# from tests/test_cli_dashboard_discovery_parity.py's established convention.

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SCAN_PATH = _REPO_ROOT / "run_scan.py"


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


def _chunked_for_nodes(tree: ast.AST):
    """Every `for ... in _chunked(...)` loop node in the tree."""
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            call = node.iter
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "_chunked"
            ):
                nodes.append(node)
    return nodes


def _calls_inside(loop_nodes, call_nodes):
    """Subset of call_nodes reachable via ast.walk from any node in loop_nodes."""
    inside = []
    for call in call_nodes:
        if any(call in ast.walk(loop_node) for loop_node in loop_nodes):
            inside.append(call)
    return inside


def _enclosing_if_tests(tree: ast.AST, target_node: ast.AST):
    """All `ast.If.test` nodes whose body (recursively) contains target_node."""
    tests = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if any(target_node in ast.walk(stmt) for stmt in node.body):
                tests.append(node.test)
    return tests


def _test_is_args_cache(test_node: ast.AST) -> bool:
    return (
        isinstance(test_node, ast.Attribute)
        and test_node.attr == "cache"
        and isinstance(test_node.value, ast.Name)
        and test_node.value.id == "args"
    )


def _test_is_args_db_path(test_node: ast.AST) -> bool:
    if isinstance(test_node, ast.Attribute):
        return (
            test_node.attr == "db_path"
            and isinstance(test_node.value, ast.Name)
            and test_node.value.id == "args"
        )
    if isinstance(test_node, ast.BoolOp):
        return any(_test_is_args_db_path(v) for v in test_node.values)
    return False


def _test_is_args_job_id_boolop(test_node: ast.AST) -> bool:
    if not isinstance(test_node, ast.BoolOp):
        return False
    for v in test_node.values:
        if (
            isinstance(v, ast.Attribute)
            and v.attr == "job_id"
            and isinstance(v.value, ast.Name)
            and v.value.id == "args"
        ):
            return True
    return False


def test_batch_checkpoint_write_is_inside_chunked_loop():
    """A per-batch write_scan_checkpoint call must exist inside the `_chunked`
    loop, alongside the pre-existing whole-stage call outside it."""
    _, tree = _parse_run_scan()
    loop_nodes = _chunked_for_nodes(tree)
    assert loop_nodes, "No `for batch in _chunked(...)` loop found in run_scan.py"

    checkpoint_calls = _find_calls(tree, "write_scan_checkpoint")
    assert len(checkpoint_calls) >= 2, (
        "Expected at least 2 write_scan_checkpoint(...) call sites (1 pre-existing "
        f"whole-stage + 1 new per-batch), found {len(checkpoint_calls)}."
    )

    inside_calls = _calls_inside(loop_nodes, checkpoint_calls)
    assert inside_calls, "No write_scan_checkpoint(...) call found inside the _chunked loop."

    def _joined_str_literal_contains(node: ast.AST, needle: str) -> bool:
        if not isinstance(node, ast.JoinedStr):
            return False
        literal_parts = "".join(
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
        return needle in literal_parts

    found_batch_stage = False
    for call in inside_calls:
        stage_arg = None
        for kw in call.keywords:
            if kw.arg == "stage":
                stage_arg = kw.value
        if stage_arg is None and len(call.args) >= 3:
            stage_arg = call.args[2]

        if _joined_str_literal_contains(stage_arg, "discovery:batch-"):
            found_batch_stage = True
        elif isinstance(stage_arg, ast.Name):
            # The stage argument may be a variable assigned to an f-string
            # earlier in the same loop body (rather than an inline literal).
            # Resolve the assignment within the enclosing loop(s).
            for loop_node in loop_nodes:
                if call not in ast.walk(loop_node):
                    continue
                for node in ast.walk(loop_node):
                    if (
                        isinstance(node, ast.Assign)
                        and any(
                            isinstance(t, ast.Name) and t.id == stage_arg.id
                            for t in node.targets
                        )
                        and _joined_str_literal_contains(node.value, "discovery:batch-")
                    ):
                        found_batch_stage = True
    assert found_batch_stage, (
        "No in-loop write_scan_checkpoint(...) call has a stage argument built from "
        "'discovery:batch-' (checked both inline f-strings and variables assigned "
        "from one within the same loop)."
    )


def test_batch_cache_write_is_inside_chunked_loop():
    """A per-batch save_cache call must exist inside the loop; the pre-existing
    whole-stage save_cache call must remain outside it."""
    _, tree = _parse_run_scan()
    loop_nodes = _chunked_for_nodes(tree)
    save_cache_calls = _find_calls(tree, "save_cache")
    assert save_cache_calls, "No save_cache(...) call sites found in run_scan.py"

    inside = _calls_inside(loop_nodes, save_cache_calls)
    outside = [c for c in save_cache_calls if c not in inside]

    assert inside, "No save_cache(...) call found inside the _chunked loop."
    assert outside, "Expected the pre-existing whole-stage save_cache(...) call outside the _chunked loop."


def test_batch_writes_are_not_gated_on_args_cache():
    """The per-batch save_cache/write_scan_checkpoint calls must be gated on
    args.db_path alone, never on args.cache (D-02)."""
    _, tree = _parse_run_scan()
    loop_nodes = _chunked_for_nodes(tree)

    save_cache_calls = _calls_inside(loop_nodes, _find_calls(tree, "save_cache"))
    checkpoint_calls = _calls_inside(loop_nodes, _find_calls(tree, "write_scan_checkpoint"))

    assert save_cache_calls, "No save_cache(...) call found inside the _chunked loop."
    assert checkpoint_calls, "No write_scan_checkpoint(...) call found inside the _chunked loop."

    for call in save_cache_calls + checkpoint_calls:
        enclosing_tests = _enclosing_if_tests(tree, call)
        assert not any(_test_is_args_cache(t) for t in enclosing_tests), (
            "A per-batch save_cache/write_scan_checkpoint call is gated on args.cache — "
            "D-02 requires the gate to be args.db_path alone."
        )
        assert any(_test_is_args_db_path(t) for t in enclosing_tests), (
            "A per-batch save_cache/write_scan_checkpoint call is not gated on args.db_path."
        )


def test_batch_writes_are_not_gated_on_args_job_id():
    """The per-batch write_scan_checkpoint call must not be gated on
    args.job_id — that gate belongs solely to update_batch_progress."""
    _, tree = _parse_run_scan()
    loop_nodes = _chunked_for_nodes(tree)
    checkpoint_calls = _calls_inside(loop_nodes, _find_calls(tree, "write_scan_checkpoint"))
    assert checkpoint_calls, "No write_scan_checkpoint(...) call found inside the _chunked loop."

    for call in checkpoint_calls:
        enclosing_tests = _enclosing_if_tests(tree, call)
        assert not any(_test_is_args_job_id_boolop(t) for t in enclosing_tests), (
            "The per-batch write_scan_checkpoint call must not be gated on args.job_id — "
            "that BoolOp gate belongs solely to update_batch_progress."
        )


def test_resume_batch_ttl_constant_is_720():
    """_RESUME_BATCH_CACHE_TTL_HOURS must be a real module-level constant equal
    to 720, and the in-loop load_cache call must reference that NAME."""
    import run_scan

    assert run_scan._RESUME_BATCH_CACHE_TTL_HOURS == 720

    _, tree = _parse_run_scan()
    loop_nodes = _chunked_for_nodes(tree)
    load_cache_calls = _calls_inside(loop_nodes, _find_calls(tree, "load_cache"))
    assert load_cache_calls, "No load_cache(...) call found inside the _chunked loop."

    found_ttl_name = False
    for call in load_cache_calls:
        for arg in call.args + [kw.value for kw in call.keywords]:
            if isinstance(arg, ast.Name) and arg.id == "_RESUME_BATCH_CACHE_TTL_HOURS":
                found_ttl_name = True
            assert not (
                isinstance(arg, ast.Attribute)
                and arg.attr == "cache_ttl_hours"
            ), "The in-loop load_cache call must not use args.cache_ttl_hours (D-06)."
    assert found_ttl_name, (
        "The in-loop load_cache(...) call must pass _RESUME_BATCH_CACHE_TTL_HOURS by name, "
        "not a literal."
    )


def test_batch_stage_completed_helper_exists():
    import run_scan

    assert callable(run_scan._batch_stage_completed)
    assert run_scan._batch_stage_completed({"discovery:batch-7"}, "discovery", 7) is True
    assert run_scan._batch_stage_completed({"discovery:batch-7"}, "discovery", 8) is False
    assert run_scan._batch_stage_completed(set(), "discovery", 1) is False


def test_no_new_checkpoint_table_or_model_change():
    models_path = _REPO_ROOT / "quirk" / "models.py"
    source = models_path.read_text()
    tree = ast.parse(source, filename=str(models_path))

    checkpoint_cls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ScanCheckpoint":
            checkpoint_cls = node
    assert checkpoint_cls is not None, "ScanCheckpoint class not found in quirk/models.py"

    column_names = set()
    for stmt in checkpoint_cls.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id != "__tablename__":
                    column_names.add(target.id)

    expected = {
        "checkpoint_id",
        "scan_run_id",
        "stage",
        "status",
        "completed_at",
        "endpoint_count",
        "partial_failure",
        "error_summary",
    }
    assert column_names == expected, (
        f"ScanCheckpoint columns changed: {column_names}. Phase 163 must add no new "
        "table or column (criterion 2)."
    )
    assert not any("batch" in name.lower() for name in column_names), (
        "No ScanCheckpoint column may reference 'batch' — batch state lives in the "
        "cache, not the checkpoint row (D-02)."
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            lname = node.name.lower()
            assert not ("batch" in lname and "checkpoint" in lname), (
                f"Unexpected new class '{node.name}' combining 'Batch' and 'Checkpoint' — "
                "criterion 2 forbids a parallel batch-checkpoint model."
            )


def test_write_scan_checkpoint_signature_unchanged():
    from quirk.cli.job_progress import write_scan_checkpoint as _wsc

    params = list(inspect.signature(_wsc).parameters.keys())
    assert params == [
        "db_path",
        "scan_run_id",
        "stage",
        "status",
        "endpoint_count",
        "partial_failure",
        "error_summary",
    ], "write_scan_checkpoint's signature must not change (D-01: zero writer changes)."


def test_only_one_discovery_call_site_each_local_regression_guard():
    """Local duplicate of the DISC-06 AST lock (D-04) so a Phase 163
    regression surfaces in this file too, not only in the parity test."""
    _, tree = _parse_run_scan()
    assert len(_find_calls(tree, "run_nmap_discovery")) == 1
    assert len(_find_calls(tree, "run_nmap_liveness_check")) == 1
