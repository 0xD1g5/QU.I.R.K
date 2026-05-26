"""Tests for quirk.cli.sensor_cmd — Phase 108 SENSOR-01/02/03."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Enroll tests (SENSOR-01)
# ---------------------------------------------------------------------------


def test_enroll_writes_sensor_yaml(tmp_path, monkeypatch):
    """SENSOR-01: enroll writes a sensor.yaml with all required keys."""
    sensor_yaml = tmp_path / "sensor.yaml"

    # Patch validate_external_url on the sensor_cmd module (already imported at module top)
    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "https://console.example"
        segment = "dmz"
        engagement = None
        config = str(sensor_yaml)
        api_token = "test-api-token-abc"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())
    assert exc_info.value.code == 0

    assert sensor_yaml.exists()
    data = yaml.safe_load(sensor_yaml.read_text())

    required_keys = {
        "console_url",
        "sensor_id",
        "segment",
        "engagement",
        "sensor_version",
        "hmac_key",
        "console_api_token",
        "allow_internal_console",  # CR-03: persisted so push honours it automatically
    }
    assert required_keys == set(data.keys())
    assert data["console_url"] == "https://console.example"
    assert data["segment"] == "dmz"
    assert data["engagement"] is None
    assert data["console_api_token"] == "test-api-token-abc"


def test_enroll_sensor_id_is_uuid(tmp_path, monkeypatch):
    """SENSOR-01: sensor_id in written sensor.yaml parses as valid UUID4."""
    sensor_yaml = tmp_path / "sensor.yaml"

    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "https://console.example"
        segment = "dmz"
        engagement = None
        config = str(sensor_yaml)
        api_token = "token"

    with pytest.raises(SystemExit):
        _cmd_enroll(Args())

    data = yaml.safe_load(sensor_yaml.read_text())
    parsed = uuid.UUID(data["sensor_id"])
    assert parsed.version == 4


def test_enroll_binds_provided_sensor_id(tmp_path, monkeypatch):
    """v5.4 enroll contract: --sensor-id binds the sensor to the console-provisioned
    identity so pushes are recognized (regression for sensor-enroll-id-mismatch 404).
    """
    sensor_yaml = tmp_path / "sensor.yaml"

    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "https://console.example"
        segment = "segment-a"
        sensor_id = "sensor-a"
        engagement = None
        config = str(sensor_yaml)
        api_token = "token"

    with pytest.raises(SystemExit):
        _cmd_enroll(Args())

    data = yaml.safe_load(sensor_yaml.read_text())
    assert data["sensor_id"] == "sensor-a"


def test_enroll_hmac_key_is_64_hex_chars(tmp_path, monkeypatch):
    """SENSOR-01: hmac_key in sensor.yaml is 64 hex characters (32 raw bytes)."""
    sensor_yaml = tmp_path / "sensor.yaml"

    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "https://console.example"
        segment = "prod"
        engagement = "eng-001"
        config = str(sensor_yaml)
        api_token = "tok"

    with pytest.raises(SystemExit):
        _cmd_enroll(Args())

    data = yaml.safe_load(sensor_yaml.read_text())
    key = data["hmac_key"]
    assert isinstance(key, str)
    assert len(key) == 64
    # Verify it is valid hex
    int(key, 16)


def test_enroll_token_not_in_yaml(tmp_path, monkeypatch, capsys):
    """SENSOR-01: raw one-time enrollment token is printed but NOT written to sensor.yaml."""
    sensor_yaml = tmp_path / "sensor.yaml"

    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "https://console.example"
        segment = "dmz"
        engagement = None
        config = str(sensor_yaml)
        api_token = "tok"

    with pytest.raises(SystemExit):
        _cmd_enroll(Args())

    captured = capsys.readouterr()
    # Extract the token from stdout
    lines = [line.strip() for line in captured.out.splitlines() if line.strip()]
    # The token line is the one after the "Enrollment token" label
    token_line = None
    for i, line in enumerate(lines):
        if "Enrollment token" in line and i + 1 < len(lines):
            token_line = lines[i + 1]
            break
        elif not any(kw in line for kw in ("Enrollment token", "Warning", "written")):
            # Might be token directly
            if len(line) > 20 and " " not in line:
                token_line = line

    yaml_content = sensor_yaml.read_text()
    if token_line:
        assert token_line not in yaml_content, "Token printed to stdout must not appear in sensor.yaml"
    # Also ensure console_api_token key value is in yaml but NOT any raw token
    data = yaml.safe_load(yaml_content)
    # The yaml should not have 'hmac_key' equal to any urlsafe token (it must be hex)
    int(data["hmac_key"], 16)  # Must be valid hex, not a urlsafe token


def test_enroll_creates_config_dir_if_absent(tmp_path, monkeypatch):
    """SENSOR-01: enroll creates the config directory if it does not exist."""
    deep_dir = tmp_path / "a" / "b" / "c"
    sensor_yaml = deep_dir / "sensor.yaml"
    assert not deep_dir.exists()

    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "https://console.example"
        segment = "dmz"
        engagement = None
        config = str(sensor_yaml)
        api_token = "tok"

    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())

    assert exc_info.value.code == 0
    assert sensor_yaml.exists()


def test_enroll_ssrf_guard_exits_nonzero(monkeypatch, capsys):
    """SENSOR-01: enroll exits non-zero with a stderr message when URL is blocked."""
    mock_result = MagicMock()
    mock_result.ok = False
    mock_result.reason = "internal_ip"
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli.sensor_cmd import _cmd_enroll

    class Args:
        console_url = "http://192.168.1.1"
        segment = "dmz"
        engagement = None
        config = "/tmp/nonexistent/sensor.yaml"
        api_token = "tok"
        allow_internal_console = False

    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "console url" in captured.err.lower()


def test_enroll_allow_internal_console_passes_rfc1918(tmp_path):
    """CR-03: enroll with --allow-internal-console accepts an RFC1918 console URL.

    This is the on-prem/lab scenario where the console lives on a private network
    (e.g. Docker console-net 10.30.0.x).  validate_external_url must be called
    with allow_internal=True so the URL is accepted.  Metadata service IPs are
    ALWAYS blocked — this test uses a plain RFC1918 address.
    """
    from quirk.util.url_allowlist import validate_external_url
    from quirk.cli.sensor_cmd import _cmd_enroll

    sensor_yaml = tmp_path / "sensor.yaml"

    class Args:
        console_url = "http://10.30.0.5:8512"
        segment = "segment-a"
        engagement = None
        config = str(sensor_yaml)
        api_token = "lab-token"
        allow_internal_console = True

    with pytest.raises(SystemExit) as exc_info:
        _cmd_enroll(Args())

    assert exc_info.value.code == 0, "enroll with --allow-internal-console must exit 0 for RFC1918 URL"
    assert sensor_yaml.exists()

    import yaml as _yaml
    data = _yaml.safe_load(sensor_yaml.read_text())
    assert data["console_url"] == "http://10.30.0.5:8512"
    # allow_internal_console must be persisted in sensor.yaml so push honours it
    assert data.get("allow_internal_console") is True, (
        "allow_internal_console=True must be written to sensor.yaml "
        "so subsequent push calls also accept the private console URL"
    )


def test_enroll_allow_internal_console_persisted_for_push(tmp_path, monkeypatch):
    """CR-03: push reads allow_internal_console from sensor.yaml and calls validate with allow_internal=True."""
    import yaml as _yaml
    from quirk.cli.sensor_cmd import _cmd_push

    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "http://10.30.0.5:8512",
        "sensor_id": str(uuid.uuid4()),
        "segment": "segment-a",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "lab-token",
        "allow_internal_console": True,
    }
    sensor_yaml.write_text(_yaml.dump(cfg))

    validate_calls = []

    import quirk.cli.sensor_cmd as sensor_cmd_mod

    original_validate = sensor_cmd_mod.validate_external_url

    def capturing_validate(url, *, allow_internal=False):
        validate_calls.append({"url": url, "allow_internal": allow_internal})
        return original_validate(url, allow_internal=allow_internal)

    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", capturing_validate)

    # Mock network + scan so the test doesn't need real infrastructure
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            return FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr(sensor_cmd_mod, "_read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr(sensor_cmd_mod, "_flush_spool", lambda *a, **kw: None)

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_push(Args())

    assert exc_info.value.code == 0
    # validate_external_url must have been called with allow_internal=True
    assert validate_calls, "validate_external_url was not called"
    assert validate_calls[0]["allow_internal"] is True, (
        "push must call validate_external_url(allow_internal=True) when "
        "sensor.yaml has allow_internal_console: true"
    )


def test_enroll_atomic_write(tmp_path, monkeypatch):
    """SENSOR-01: atomic write — no truncated file on exception before os.replace."""
    sensor_yaml = tmp_path / "sensor.yaml"

    mock_result = MagicMock()
    mock_result.ok = True
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "validate_external_url", lambda *a, **kw: mock_result)

    from quirk.cli import sensor_cmd

    # Patch yaml.dump to raise on the write
    original_dump = yaml.dump
    call_count = {"n": 0}

    def patched_dump(data, f, **kwargs):
        call_count["n"] += 1
        raise RuntimeError("Simulated disk-full")

    monkeypatch.setattr(yaml, "dump", patched_dump)

    class Args:
        console_url = "https://console.example"
        segment = "dmz"
        engagement = None
        config = str(sensor_yaml)
        api_token = "tok"

    with pytest.raises(RuntimeError):
        sensor_cmd._cmd_enroll(Args())

    # The real sensor.yaml must not have been created (tempfile cleanup + no os.replace)
    assert not sensor_yaml.exists()

    monkeypatch.setattr(yaml, "dump", original_dump)


# ---------------------------------------------------------------------------
# Envelope + compression tests (SENSOR-02)
# ---------------------------------------------------------------------------


def test_build_envelope_keys(monkeypatch):
    """SENSOR-02: _build_envelope returns exactly the specified key set; no received_at."""
    from quirk.cli.sensor_cmd import _build_envelope

    sensor_cfg = {
        "sensor_version": "5.4.0",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
    }
    envelope = _build_envelope(sensor_cfg, [])

    expected_keys = {
        "payload_id",
        "pushed_at",
        "schema_version",
        "sensor_version",
        "sensor_id",
        "segment",
        "findings",
    }
    assert set(envelope.keys()) == expected_keys
    assert "received_at" not in envelope


def test_build_compressed_payload_roundtrip():
    """SENSOR-02: compressed payload decompresses to the original envelope."""
    import zstandard

    from quirk.cli.sensor_cmd import _build_compressed_payload, _build_envelope

    sensor_cfg = {
        "sensor_version": "5.4.0",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
    }
    envelope = _build_envelope(sensor_cfg, [])
    compressed = _build_compressed_payload(envelope)
    raw = zstandard.ZstdDecompressor().decompress(compressed)
    recovered = json.loads(raw.decode("utf-8"))
    assert recovered == envelope


def test_hmac_signature_format():
    """SENSOR-02: signature header is 'hmac-sha256=' + hex HMAC for fixed inputs."""
    import hashlib
    import hmac as _hmac

    from quirk.cli.sensor_cmd import _sign

    key_bytes = b"\x00" * 32
    body = b"test body"
    sig = _sign(body, key_bytes)
    expected_hex = _hmac.new(key_bytes, body, hashlib.sha256).hexdigest()
    assert sig == f"hmac-sha256={expected_hex}"


def test_push_posts_to_correct_url(tmp_path, monkeypatch):
    """SENSOR-02: push POSTs to console_url + '/api/sensor/push' with correct headers."""
    sensor_yaml = tmp_path / "sensor.yaml"
    sid = str(uuid.uuid4())
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": sid,
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    captured_calls = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, **kwargs):
            self._kwargs = kwargs

        def post(self, url, headers, content):
            captured_calls.append(
                {"url": url, "headers": headers, "content": content, "kwargs": self._kwargs}
            )
            return FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient)

    # Mock subprocess so no real scan runs
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"", b"")
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)

    # Mock DB read to return empty endpoint list
    monkeypatch.setattr(
        "quirk.cli.sensor_cmd._read_scan_endpoints",
        lambda db_path: [],
    )

    # Mock spool flush to no-op
    monkeypatch.setattr(
        "quirk.cli.sensor_cmd._flush_spool",
        lambda client, url, headers_fn: None,
    )

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    # Use a temp output dir
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_push(Args())

    assert exc_info.value.code == 0
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["url"] == "https://console.example/api/sensor/push"
    assert call["headers"]["Authorization"] == "Bearer bearer-tok"
    assert call["headers"]["Content-Type"] == "application/octet-stream"
    assert call["headers"]["X-Sensor-Signature"].startswith("hmac-sha256=")
    # verify=True and follow_redirects=False must be in constructor kwargs
    assert call["kwargs"].get("verify") is True
    assert call["kwargs"].get("follow_redirects") is False


def test_push_retry_on_5xx(tmp_path, monkeypatch):
    """SENSOR-02: 5xx response triggers retry; 4xx does not."""
    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    import httpx

    call_counts = {"n": 0}

    class FakeResponse5xx:
        status_code = 503

        def raise_for_status(self):
            raise httpx.HTTPStatusError("503", request=None, response=self)

    class FakeClient5xx:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            call_counts["n"] += 1
            return FakeResponse5xx()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient5xx)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("quirk.cli.sensor_cmd._flush_spool", lambda *a, **kw: None)
    # Prevent spool write on failure
    monkeypatch.setattr("quirk.cli.sensor_cmd._spool_payload", lambda *a, **kw: None)

    # Speed up retries so test doesn't wait 2-60 seconds per attempt
    import tenacity
    monkeypatch.setattr("quirk.cli.sensor_cmd._do_push.retry.wait", tenacity.wait_none())

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_push(Args())

    assert call_counts["n"] > 1, "5xx should trigger retries"


def test_push_no_retry_on_4xx(tmp_path, monkeypatch):
    """SENSOR-02: 4xx response does NOT trigger retry — exactly 1 attempt."""
    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    call_counts = {"n": 0}

    class FakeResponse4xx:
        status_code = 401

        def raise_for_status(self):
            pass  # 4xx does NOT call raise_for_status per design

    class FakeClient4xx:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            call_counts["n"] += 1
            return FakeResponse4xx()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient4xx)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("quirk.cli.sensor_cmd._flush_spool", lambda *a, **kw: None)

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_push(Args())

    assert call_counts["n"] == 1, "4xx must not trigger retry"


def test_push_connect_error_retries(tmp_path, monkeypatch):
    """SENSOR-02: ConnectError retries up to 5 attempts."""
    import httpx

    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    call_counts = {"n": 0}

    class FakeClientConnectError:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            call_counts["n"] += 1
            raise httpx.ConnectError("Connection refused")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClientConnectError)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("quirk.cli.sensor_cmd._flush_spool", lambda *a, **kw: None)
    # Prevent writing to spool dir
    monkeypatch.setattr("quirk.cli.sensor_cmd._spool_payload", lambda *a, **kw: None)

    # Patch tenacity wait to speed up test
    import tenacity

    monkeypatch.setattr(
        "quirk.cli.sensor_cmd._do_push.retry.wait",
        tenacity.wait_none(),
    )

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_push(Args())

    assert call_counts["n"] == 5, f"Expected 5 retry attempts, got {call_counts['n']}"


def test_push_409_treated_as_success(tmp_path, monkeypatch):
    """SENSOR-02: 409 response is treated as already-delivered success (no error exit)."""
    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    class FakeResponse409:
        status_code = 409

        def raise_for_status(self):
            pass

    class FakeClient409:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            return FakeResponse409()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient409)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("quirk.cli.sensor_cmd._flush_spool", lambda *a, **kw: None)

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_push(Args())
    assert exc_info.value.code == 0


def test_push_uses_subprocess_not_import(monkeypatch):
    """SENSOR-02: push invokes run_scan via subprocess, never by calling main() directly."""
    import pathlib

    src = pathlib.Path(__file__).resolve().parent.parent / "quirk" / "cli" / "sensor_cmd.py"
    code = src.read_text()
    assert "run_scan.main(" not in code, "sensor_cmd.py must not call run_scan.main() directly"


# ---------------------------------------------------------------------------
# Spool tests (SENSOR-03)
# ---------------------------------------------------------------------------


def test_spool_on_connect_failure(tmp_path, monkeypatch):
    """SENSOR-03: connection failure after retries → payload written to spool dir."""
    import httpx

    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    spool_dir = tmp_path / "spool"

    class FakeClientConnectError:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            raise httpx.ConnectError("Connection refused")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClientConnectError)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("quirk.cli.sensor_cmd._flush_spool", lambda *a, **kw: None)

    # Redirect spool dir to tmp_path
    import quirk.cli.sensor_cmd as sensor_cmd_mod

    monkeypatch.setattr(sensor_cmd_mod, "_spool_dir", lambda: spool_dir)

    # Speed up retries
    import tenacity

    monkeypatch.setattr(
        "quirk.cli.sensor_cmd._do_push.retry.wait",
        tenacity.wait_none(),
    )

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_push(Args())

    spooled_files = list(spool_dir.glob("*.json.zst"))
    assert len(spooled_files) == 1, f"Expected 1 spooled file, found {len(spooled_files)}"
    # Filename must be a valid UUID
    stem = spooled_files[0].stem.replace(".json", "")
    uuid.UUID(stem)


def test_spool_flush_delivers_and_unlinks(tmp_path, monkeypatch):
    """SENSOR-03: on next push with working console, spooled file is re-pushed and unlinked."""
    import httpx

    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    sid = str(uuid.uuid4())
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": sid,
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    spool_dir = tmp_path / "spool"
    spool_dir.mkdir()

    # Pre-populate spool with a fake payload
    fake_payload_id = str(uuid.uuid4())
    fake_body = b"fakepayloadbytes"
    spool_file = spool_dir / f"{fake_payload_id}.json.zst"
    spool_file.write_bytes(fake_body)

    delivered = []

    class FakeResponse200:
        status_code = 200

        def raise_for_status(self):
            pass

    class FakeClient200:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            delivered.append(content)
            return FakeResponse200()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient200)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])

    import quirk.cli.sensor_cmd as sensor_cmd_mod

    monkeypatch.setattr(sensor_cmd_mod, "_spool_dir", lambda: spool_dir)

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_push(Args())

    assert exc_info.value.code == 0
    # Spooled file should be unlinked after successful delivery
    assert not spool_file.exists(), "Delivered spooled file must be unlinked"


def test_spool_evict_on_max_files(tmp_path, monkeypatch, capsys):
    """SENSOR-03: exceeding _SPOOL_MAX_FILES evicts oldest file with stderr warning."""
    import quirk.cli.sensor_cmd as sensor_cmd_mod

    spool_dir = tmp_path / "spool"
    spool_dir.mkdir()

    # Create _SPOOL_MAX_FILES files so the dir is full
    max_files = sensor_cmd_mod._SPOOL_MAX_FILES
    for i in range(max_files):
        f = spool_dir / f"{uuid.uuid4()}.json.zst"
        f.write_bytes(b"x")
        # Ensure mtime ordering
        import time

        time.sleep(0.001)

    oldest = sorted(spool_dir.glob("*.json.zst"), key=lambda p: p.stat().st_mtime)[0]

    monkeypatch.setattr(sensor_cmd_mod, "_spool_dir", lambda: spool_dir)
    sensor_cmd_mod._evict_if_full(spool_dir)

    captured = capsys.readouterr()
    assert "spool" in captured.err.lower()
    assert not oldest.exists(), "Oldest file must be evicted"


def test_spool_409_unlinks_file(tmp_path, monkeypatch):
    """SENSOR-03: a 409 response on a spooled re-push unlinks the file."""
    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    sid = str(uuid.uuid4())
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": sid,
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    spool_dir = tmp_path / "spool"
    spool_dir.mkdir()

    # Pre-populate spool
    fake_payload_id = str(uuid.uuid4())
    spool_file = spool_dir / f"{fake_payload_id}.json.zst"
    spool_file.write_bytes(b"fakepayload")

    class FakeResponse409:
        status_code = 409

        def raise_for_status(self):
            pass

    class FakeClient409:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            return FakeResponse409()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClient409)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])

    import quirk.cli.sensor_cmd as sensor_cmd_mod

    monkeypatch.setattr(sensor_cmd_mod, "_spool_dir", lambda: spool_dir)

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_push(Args())

    assert exc_info.value.code == 0
    assert not spool_file.exists(), "409 response must unlink the spooled file"


def test_spool_filename_is_uuid_pattern(tmp_path, monkeypatch):
    """SENSOR-03: spool filenames are {uuid4}.json.zst — no operator-controlled components."""
    import httpx

    sensor_yaml = tmp_path / "sensor.yaml"
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": str(uuid.uuid4()),
        "segment": "dmz",
        "engagement": None,
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "bearer-tok",
    }
    sensor_yaml.write_text(yaml.dump(cfg))

    spool_dir = tmp_path / "spool"

    class FakeClientConnectError:
        def __init__(self, **kwargs):
            pass

        def post(self, url, headers, content):
            raise httpx.ConnectError("Connection refused")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("httpx.Client", FakeClientConnectError)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    monkeypatch.setattr("quirk.cli.sensor_cmd._read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("quirk.cli.sensor_cmd._flush_spool", lambda *a, **kw: None)

    import quirk.cli.sensor_cmd as sensor_cmd_mod

    monkeypatch.setattr(sensor_cmd_mod, "_spool_dir", lambda: spool_dir)

    import tenacity

    monkeypatch.setattr(
        "quirk.cli.sensor_cmd._do_push.retry.wait",
        tenacity.wait_none(),
    )

    from quirk.cli.sensor_cmd import _cmd_push

    class Args:
        config = str(sensor_yaml)
        scan_config = "config.yaml"

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_push(Args())

    spooled_files = list(spool_dir.glob("*.json.zst"))
    assert len(spooled_files) == 1
    fname = spooled_files[0].name
    # Must match <uuid>.json.zst
    assert fname.endswith(".json.zst")
    stem = fname[: -len(".json.zst")]
    parsed = uuid.UUID(stem)
    assert parsed.version == 4
    # No path separators or user-controlled components
    assert "/" not in fname
    assert "\\" not in fname


# ---------------------------------------------------------------------------
# Export-results tests (SENSOR-04)
# ---------------------------------------------------------------------------


def _make_sensor_cfg(tmp_path) -> tuple:
    """Return (sensor_yaml_path, sensor_cfg_dict) for export tests."""
    sid = str(uuid.uuid4())
    hmac_key = os.urandom(32).hex()
    cfg = {
        "console_url": "https://console.example",
        "sensor_id": sid,
        "segment": "air-gap-dmz",
        "engagement": "eng-999",
        "sensor_version": "5.4.0",
        "hmac_key": hmac_key,
        "console_api_token": "tok",
    }
    sensor_yaml = tmp_path / "sensor.yaml"
    sensor_yaml.write_text(yaml.dump(cfg))
    return str(sensor_yaml), cfg


def test_export_writes_qpush_file(tmp_path, monkeypatch):
    """SENSOR-04: export-results writes {sensor_id}-{payload_id}.qpush to --output dir."""
    sensor_yaml, sensor_cfg = _make_sensor_cfg(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "_read_scan_endpoints", lambda db_path: [])

    from quirk.cli.sensor_cmd import _cmd_export_results

    class Args:
        config = sensor_yaml
        scan_config = "config.yaml"
        output = str(output_dir)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_export_results(Args())

    assert exc_info.value.code == 0
    qpush_files = list(output_dir.glob("*.qpush"))
    assert len(qpush_files) == 1, f"Expected 1 .qpush file, found {len(qpush_files)}"
    fname = qpush_files[0].name
    assert fname.startswith(sensor_cfg["sensor_id"]), (
        f"Filename must start with sensor_id; got {fname}"
    )
    assert fname.endswith(".qpush"), f"Filename must end with .qpush; got {fname}"


def test_export_filename_contains_payload_id(tmp_path, monkeypatch):
    """SENSOR-04: .qpush filename is {sensor_id}-{payload_id}.qpush; both are valid UUIDs."""
    sensor_yaml, sensor_cfg = _make_sensor_cfg(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "_read_scan_endpoints", lambda db_path: [])

    from quirk.cli.sensor_cmd import _cmd_export_results

    class Args:
        config = sensor_yaml
        scan_config = "config.yaml"
        output = str(output_dir)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_export_results(Args())

    fname = list(output_dir.glob("*.qpush"))[0].name
    # Format: {sensor_id}-{payload_id}.qpush
    # Strip the sensor_id prefix + hyphen + payload_id = UUID-UUID.qpush
    sid = sensor_cfg["sensor_id"]
    assert fname.startswith(sid + "-")
    payload_part = fname[len(sid) + 1 : -len(".qpush")]
    parsed = uuid.UUID(payload_part)
    assert parsed.version == 4


def test_export_body_byte_identical_to_push_body(tmp_path, monkeypatch):
    """SENSOR-04: compressed-payload body in .qpush is byte-identical to the push request body.

    Both export and push call _build_envelope and _build_compressed_payload with identical
    inputs (monkeypatched fixed payload_id and pushed_at).  The resulting compressed bytes
    MUST be identical — this is the single shared serialization path invariant.

    WR-03 note: the .qpush file now has a framing header prepended:
        {"hmac-sha256": "hmac-sha256=<hex>"}\\n<compressed-body>
    This test extracts the compressed body component and asserts it equals the push body.
    The whole-file bytes differ (header + body vs body-only) because the HMAC signature
    travels as file framing for air-gap integrity, not inside the compressed payload.
    """
    import zstandard

    sensor_yaml, sensor_cfg = _make_sensor_cfg(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    # Fix payload_id and pushed_at so both push and export produce identical envelopes
    fixed_payload_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    fixed_pushed_at = "2026-05-25T12:00:00Z"

    import quirk.cli.sensor_cmd as sensor_cmd_mod

    original_build_envelope = sensor_cmd_mod._build_envelope

    def patched_build_envelope(sc, endpoints):
        env = original_build_envelope(sc, endpoints)
        env["payload_id"] = fixed_payload_id
        env["pushed_at"] = fixed_pushed_at
        return env

    monkeypatch.setattr(sensor_cmd_mod, "_build_envelope", patched_build_envelope)
    monkeypatch.setattr(sensor_cmd_mod, "_read_scan_endpoints", lambda db_path: [])
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())

    from quirk.cli.sensor_cmd import _cmd_export_results, _build_compressed_payload

    class Args:
        config = sensor_yaml
        scan_config = "config.yaml"
        output = str(output_dir)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_export_results(Args())
    assert exc_info.value.code == 0

    # Read the .qpush file bytes and extract the compressed body component.
    # WR-03: the file starts with a JSON header line followed by '\n' and the body.
    qpush_file = list(output_dir.glob("*.qpush"))[0]
    qpush_raw = qpush_file.read_bytes()

    assert qpush_raw.startswith(b"{"), (
        ".qpush file must start with the WR-03 framing header"
    )
    newline_pos = qpush_raw.find(b"\n")
    assert newline_pos != -1, ".qpush framing header must end with a newline"
    qpush_body = qpush_raw[newline_pos + 1:]

    # Reproduce what push would have sent as the request body with same inputs
    expected_envelope = patched_build_envelope(sensor_cfg, [])
    expected_body = _build_compressed_payload(expected_envelope)

    # The compressed body component of the .qpush file must equal the push request body.
    assert qpush_body == expected_body, (
        "export .qpush compressed-body component must be byte-identical to the push "
        "request body; export must reuse _build_compressed_payload, not fork serialization"
    )

    # Additionally verify the body decompresses to a valid envelope
    raw = zstandard.ZstdDecompressor().decompress(qpush_body)
    recovered = json.loads(raw.decode("utf-8"))
    assert recovered["payload_id"] == fixed_payload_id
    assert recovered["sensor_id"] == sensor_cfg["sensor_id"]


def test_export_decompresses_to_canonical_envelope_keys(tmp_path, monkeypatch):
    """SENSOR-04: .qpush body decompresses to an envelope with the canonical key set."""
    import zstandard

    sensor_yaml, sensor_cfg = _make_sensor_cfg(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "_read_scan_endpoints", lambda db_path: [])

    from quirk.cli.sensor_cmd import _cmd_export_results

    class Args:
        config = sensor_yaml
        scan_config = "config.yaml"
        output = str(output_dir)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit):
            _cmd_export_results(Args())

    # WR-03: strip the framing header line before decompressing
    qpush_raw = list(output_dir.glob("*.qpush"))[0].read_bytes()
    newline_pos = qpush_raw.find(b"\n")
    qpush_body = qpush_raw[newline_pos + 1:] if newline_pos != -1 else qpush_raw
    raw = zstandard.ZstdDecompressor().decompress(qpush_body)
    envelope = json.loads(raw.decode("utf-8"))

    expected_keys = {
        "payload_id",
        "pushed_at",
        "schema_version",
        "sensor_version",
        "sensor_id",
        "segment",
        "findings",
    }
    assert set(envelope.keys()) == expected_keys
    assert "received_at" not in envelope


def test_export_no_network_call(tmp_path, monkeypatch):
    """SENSOR-04: export-results does NOT make any httpx network calls."""
    sensor_yaml, _ = _make_sensor_cfg(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    # Make httpx.Client raise if instantiated
    def _fail_if_httpx_called(*a, **kw):
        raise AssertionError("export-results must not make any httpx network calls")

    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _make_mock_proc())
    import quirk.cli.sensor_cmd as sensor_cmd_mod
    monkeypatch.setattr(sensor_cmd_mod, "_read_scan_endpoints", lambda db_path: [])

    try:
        import httpx
        monkeypatch.setattr(httpx, "Client", _fail_if_httpx_called)
    except ImportError:
        pass

    from quirk.cli.sensor_cmd import _cmd_export_results

    class Args:
        config = sensor_yaml
        scan_config = "config.yaml"
        output = str(output_dir)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr("tempfile.mkdtemp", lambda: td)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_export_results(Args())

    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_proc():
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"", b"")
    return mock_proc
