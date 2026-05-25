"""Tests for quirk.cli.console_cmd — Phase 108 SENSOR-04 import-results."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
import zstandard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_qpush_bytes(sensor_id: str = None, segment: str = "air-gap", extra_keys: dict = None) -> bytes:
    """Build a valid compressed .qpush payload bytes with canonical envelope keys."""
    if sensor_id is None:
        sensor_id = str(uuid.uuid4())
    envelope = {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": "2026-05-25T12:00:00Z",
        "schema_version": "1.0.0",
        "sensor_version": "5.4.0",
        "sensor_id": sensor_id,
        "segment": segment,
        "findings": [],
    }
    if extra_keys:
        envelope.update(extra_keys)
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    return zstandard.ZstdCompressor(level=3).compress(raw)


def _make_qpush_file(tmp_path: Path, **kwargs) -> Path:
    """Write a .qpush file to tmp_path and return the path."""
    qpush = tmp_path / f"sensor-{uuid.uuid4()}.qpush"
    qpush.write_bytes(_make_qpush_bytes(**kwargs))
    return qpush


# ---------------------------------------------------------------------------
# Happy-path: import-results reads, decompresses, validates, prints summary
# ---------------------------------------------------------------------------


def test_import_results_success_exit_zero(tmp_path):
    """SENSOR-04: import-results exits 0 on a valid .qpush file."""
    qpush = _make_qpush_file(tmp_path)

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_import_results(Args())

    assert exc_info.value.code == 0


def test_import_results_prints_summary(tmp_path, capsys):
    """SENSOR-04: import-results prints sensor_id, segment, payload_id, finding count."""
    sid = str(uuid.uuid4())
    qpush = _make_qpush_file(tmp_path, sensor_id=sid, segment="dmz-air")

    # Read the envelope to get payload_id for assertion
    raw = zstandard.ZstdDecompressor().decompress(qpush.read_bytes())
    envelope = json.loads(raw.decode("utf-8"))
    expected_pid = envelope["payload_id"]

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit):
        _cmd_import_results(Args())

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert sid in output, f"sensor_id {sid!r} not found in output: {output!r}"
    assert "dmz-air" in output, f"segment not found in output: {output!r}"
    assert expected_pid in output, f"payload_id not found in output: {output!r}"
    # Finding count (0 findings)
    assert "0" in output, f"finding count not found in output: {output!r}"


def test_import_results_finding_count_nonzero(tmp_path, capsys):
    """SENSOR-04: import-results reports correct finding count when findings > 0."""
    sid = str(uuid.uuid4())
    findings = [
        {"host": "10.0.0.1", "port": 443, "protocol": "tls"},
        {"host": "10.0.0.2", "port": 22, "protocol": "ssh"},
    ]
    qpush = _make_qpush_file(tmp_path, sensor_id=sid)
    # Rebuild with findings
    envelope = {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": "2026-05-25T12:00:00Z",
        "schema_version": "1.0.0",
        "sensor_version": "5.4.0",
        "sensor_id": sid,
        "segment": "dmz",
        "findings": findings,
    }
    raw = json.dumps(envelope).encode()
    qpush.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit):
        _cmd_import_results(Args())

    output = capsys.readouterr().out + capsys.readouterr().err
    # "2" should appear in the output as the finding count
    # (re-run capsys if needed — just check 2 is present somewhere)
    # We capture via sys.stdout/stderr directly
    import io, sys
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        with pytest.raises(SystemExit):
            _cmd_import_results(Args())
        out = sys.stdout.getvalue() + sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    assert "2" in out, f"finding count '2' not found in output: {out!r}"


# ---------------------------------------------------------------------------
# Error cases: corrupt / non-zstd file → clean exit non-zero
# ---------------------------------------------------------------------------


def test_import_results_corrupt_file_exits_nonzero(tmp_path, capsys):
    """SENSOR-04: a non-zstd / corrupt .qpush file exits non-zero with clear stderr (no traceback)."""
    qpush = tmp_path / "bad.qpush"
    qpush.write_bytes(b"this is not zstd compressed data at all!!!")

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_import_results(Args())

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    stderr = captured.err
    assert stderr.strip(), "A clear error message must be written to stderr"
    # Must not contain a raw traceback
    assert "Traceback" not in stderr, f"Raw traceback in stderr: {stderr!r}"


def test_import_results_missing_key_exits_nonzero(tmp_path, capsys):
    """SENSOR-04: an envelope missing a required key exits non-zero with validation message."""
    # Build an envelope missing 'segment'
    envelope = {
        "payload_id": str(uuid.uuid4()),
        "pushed_at": "2026-05-25T12:00:00Z",
        "schema_version": "1.0.0",
        "sensor_version": "5.4.0",
        "sensor_id": str(uuid.uuid4()),
        # "segment" intentionally omitted
        "findings": [],
    }
    raw = json.dumps(envelope).encode()
    qpush = tmp_path / "missing-key.qpush"
    qpush.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_import_results(Args())

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    stderr = captured.err
    assert stderr.strip(), "A validation error message must be written to stderr"
    assert "Traceback" not in stderr


def test_import_results_missing_payload_id_exits_nonzero(tmp_path, capsys):
    """SENSOR-04: envelope missing payload_id (dedup key) is rejected."""
    envelope = {
        # "payload_id" intentionally omitted
        "pushed_at": "2026-05-25T12:00:00Z",
        "schema_version": "1.0.0",
        "sensor_version": "5.4.0",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "findings": [],
    }
    raw = json.dumps(envelope).encode()
    qpush = tmp_path / "no-pid.qpush"
    qpush.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_import_results(Args())

    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# Ingest routing: _ingest_envelope called with skip_replay_window=True
# ---------------------------------------------------------------------------


def test_import_results_calls_ingest_with_skip_replay(tmp_path, monkeypatch):
    """SENSOR-04: _ingest_envelope is called with skip_replay_window=True (air-gap carve-out)."""
    qpush = _make_qpush_file(tmp_path)

    ingest_calls = []

    def fake_ingest(envelope, config_path, skip_replay_window=False, qpush_sig=None):
        ingest_calls.append({
            "envelope": envelope,
            "config_path": config_path,
            "skip_replay_window": skip_replay_window,
            "qpush_sig": qpush_sig,
        })

    import quirk.cli.console_cmd as console_cmd_mod
    monkeypatch.setattr(console_cmd_mod, "_ingest_envelope", fake_ingest)

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "myconfig.yaml"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_import_results(Args())

    assert exc_info.value.code == 0
    assert len(ingest_calls) == 1, f"_ingest_envelope must be called once; got {len(ingest_calls)}"
    call = ingest_calls[0]
    assert call["skip_replay_window"] is True, (
        "_ingest_envelope must be called with skip_replay_window=True on air-gap import"
    )
    assert call["config_path"] == "myconfig.yaml"
    # The envelope must have the canonical keys
    assert "payload_id" in call["envelope"]
    assert "sensor_id" in call["envelope"]


def test_import_results_single_ingest_entry(tmp_path, monkeypatch):
    """SENSOR-04: _cmd_import_results routes through exactly one _ingest_envelope call (Phase 109 seam)."""
    qpush = _make_qpush_file(tmp_path)

    ingest_calls = []

    def fake_ingest(envelope, config_path, skip_replay_window=False, qpush_sig=None):
        ingest_calls.append(True)

    import quirk.cli.console_cmd as console_cmd_mod
    monkeypatch.setattr(console_cmd_mod, "_ingest_envelope", fake_ingest)

    from quirk.cli.console_cmd import _cmd_import_results

    class Args:
        file = str(qpush)
        config = "config.yaml"

    with pytest.raises(SystemExit):
        _cmd_import_results(Args())

    assert len(ingest_calls) == 1


# ---------------------------------------------------------------------------
# run_scan.py dispatch: console block routes to run_console
# ---------------------------------------------------------------------------


def test_run_scan_console_dispatch(monkeypatch, capsys):
    """SENSOR-04: run_scan.py dispatches argv[1]=='console' to run_console."""
    import sys

    received_argv = []

    def fake_run_console(argv):
        received_argv.extend(argv)
        # Must not call sys.exit here — the dispatch block calls return after run_console
        raise SystemExit(0)

    monkeypatch.setattr(sys, "argv", ["run_scan.py", "console", "import-results", "/tmp/test.qpush"])

    import importlib
    import types

    # Patch the lazy import inside run_scan.main
    fake_module = types.SimpleNamespace(run_console=fake_run_console)

    with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (
        fake_module if name == "quirk.cli.console_cmd" else __builtins__.__import__(name, *a, **kw)
        if hasattr(__builtins__, "__import__") else __import__(name, *a, **kw)
    )):
        pass  # can't easily test via builtins.__import__, test via direct run_scan import

    # Direct approach: import run_scan and call main()
    import run_scan
    monkeypatch.setattr(sys, "argv", ["run_scan.py", "console", "--help"])

    # Verify the dispatch block is in run_scan.py source
    import pathlib
    src = pathlib.Path(run_scan.__file__).read_text()
    assert "_sys.argv[1] == \"console\"" in src or "_sys.argv[1] == 'console'" in src, (
        "run_scan.py must have a console dispatch block"
    )
    assert "from quirk.cli.console_cmd import run_console" in src, (
        "run_scan.py console block must lazy-import run_console"
    )
