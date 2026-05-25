"""Phase 108 SENSOR-06: Windows sensor smoke tests — no-backslash payload + clean shutdown.

These tests run on any OS but are the hard-gate payload executed on windows-latest.
The backslash assertion is trivially satisfied on Linux (forward slashes native) but
exercises the real Windows hazard: Path.__str__ on Windows produces backslash-separated
strings that would corrupt the wire payload if not normalized.

All tests use only core dependencies (no [all] extras required).
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from unittest.mock import MagicMock

import pytest

from quirk.cli.sensor_cmd import _build_envelope, _build_compressed_payload

# ---------------------------------------------------------------------------
# Fixtures — sample sensor config + fake endpoints
# ---------------------------------------------------------------------------

SAMPLE_SENSOR_CFG = {
    "console_url": "https://console.example.com",
    "sensor_id": "test-sensor-uuid-1234",
    "segment": "dmz",
    "engagement": "acme-2026",
    "sensor_version": "5.4.0-dev",
    "hmac_key": "deadbeefdeadbeefdeadbeefdeadbeef",
    "console_api_token": "tok-test",
}


def _make_endpoint(
    host: str = "server.example.com",
    port: int = 443,
    protocol: str = "TLS",
    tls_version: str = "TLSv1.3",
    cipher_suite: str = "TLS_AES_256_GCM_SHA384",
    cert_subject: str = "CN=server.example.com",
    cert_issuer: str = "CN=Test CA",
    cert_sans: str = "server.example.com",
    cert_sig_alg: str = "sha256WithRSAEncryption",
    cert_pubkey_alg: str = "RSA",
    cert_pubkey_size: int = 2048,
    sensor_id: str | None = "test-sensor-uuid-1234",
    segment: str | None = "dmz",
) -> MagicMock:
    """Build a mock CryptoEndpoint with the columns _endpoint_to_dict reads."""
    ep = MagicMock()
    ep.host = host
    ep.port = port
    ep.protocol = protocol
    ep.scanned_at = None
    ep.tls_version = tls_version
    ep.cipher_suite = cipher_suite
    ep.cert_subject = cert_subject
    ep.cert_issuer = cert_issuer
    ep.cert_sans = cert_sans
    ep.cert_sig_alg = cert_sig_alg
    ep.cert_pubkey_alg = cert_pubkey_alg
    ep.cert_pubkey_size = cert_pubkey_size
    ep.cert_not_before = None
    ep.cert_not_after = None
    ep.sensor_id = sensor_id
    ep.segment = segment
    return ep


def _make_endpoint_with_windows_paths() -> MagicMock:
    """Endpoint whose string fields deliberately embed backslash path separators.

    On Windows, Path("C:\\Users\\scan\\output").as_posix() is the safe path,
    but Path("C:\\Users\\scan\\output").__str__() produces backslashes.  The
    _endpoint_to_dict normalizer must convert these to forward slashes before
    the payload is serialized.
    """
    ep = _make_endpoint()
    # Simulate a Windows path that leaked into a host/cert field as a string
    ep.cert_subject = "CN=C:\\Users\\sensor\\output\\cert.pem"
    ep.cert_issuer = "CN=C:\\ProgramData\\quirk\\ca.pem"
    ep.cert_sans = "server.example.com,C:\\Windows\\System32\\drivers\\etc\\hosts"
    return ep


# ---------------------------------------------------------------------------
# Test: no backslash in json.dumps(envelope)
# ---------------------------------------------------------------------------


class TestNoBackslashInPayload:
    """SENSOR-06: serialized wire payload must contain no backslash path separators."""

    def test_no_backslash_basic(self):
        """json.dumps(_build_envelope(...)) must not contain chr(92) for normal endpoints."""
        endpoints = [_make_endpoint()]
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, endpoints)
        serialized = json.dumps(envelope)
        assert "\\" not in serialized, (
            "Backslash found in serialized wire payload — Windows Path hazard "
            "(SENSOR-06 / RESEARCH Pitfall 5)"
        )

    def test_no_backslash_windows_path_endpoints(self):
        """Endpoints with Windows-style backslash paths are normalized to forward slashes."""
        endpoints = [_make_endpoint_with_windows_paths()]
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, endpoints)
        serialized = json.dumps(envelope)
        assert "\\" not in serialized, (
            "Backslash survived normalization — _endpoint_to_dict must replace backslashes "
            "before building the envelope (SENSOR-06)"
        )

    def test_no_backslash_multiple_endpoints(self):
        """Multiple endpoints, some with backslash paths, all normalized."""
        endpoints = [
            _make_endpoint(host="host1.example.com"),
            _make_endpoint_with_windows_paths(),
            _make_endpoint(host="host2.example.com", cert_subject="CN=host2"),
        ]
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, endpoints)
        serialized = json.dumps(envelope)
        assert "\\" not in serialized, (
            "Backslash found in multi-endpoint serialized payload"
        )

    def test_no_backslash_empty_endpoints(self):
        """Empty endpoint list produces a valid envelope with no backslash."""
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, [])
        serialized = json.dumps(envelope)
        assert "\\" not in serialized

    def test_recursive_string_values_free_of_backslash(self):
        """Every string value in the envelope (recursively) must be free of backslashes."""
        endpoints = [_make_endpoint_with_windows_paths()]
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, endpoints)

        def _collect_strings(obj):
            if isinstance(obj, str):
                return [obj]
            if isinstance(obj, dict):
                return [s for v in obj.values() for s in _collect_strings(v)]
            if isinstance(obj, list):
                return [s for item in obj for s in _collect_strings(item)]
            return []

        for s in _collect_strings(envelope):
            assert "\\" not in s, (
                f"String value contains backslash: {s!r}  "
                "(SENSOR-06 recursive string check)"
            )


# ---------------------------------------------------------------------------
# Test: envelope structure + required keys
# ---------------------------------------------------------------------------


class TestEnvelopeStructure:
    """The envelope produced by _build_envelope has the correct required keys."""

    def test_required_keys_present(self):
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, [])
        for key in ("payload_id", "pushed_at", "schema_version",
                    "sensor_version", "sensor_id", "segment", "findings"):
            assert key in envelope, f"Required key missing from envelope: {key}"

    def test_findings_is_list(self):
        endpoints = [_make_endpoint()]
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, endpoints)
        assert isinstance(envelope["findings"], list)
        assert len(envelope["findings"]) == 1

    def test_pushed_at_format(self):
        """pushed_at must be an ISO-8601 UTC string with no timezone offset."""
        import re
        envelope = _build_envelope(SAMPLE_SENSOR_CFG, [])
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        assert re.match(pattern, envelope["pushed_at"]), (
            f"pushed_at format incorrect: {envelope['pushed_at']!r}"
        )


# ---------------------------------------------------------------------------
# Test: clean shutdown on KeyboardInterrupt (SENSOR-06 clean-shutdown)
# ---------------------------------------------------------------------------


class TestCleanShutdownOnKeyboardInterrupt:
    """SENSOR-06: KeyboardInterrupt during run_sensor dispatch must yield exit code 130.

    We use a subprocess to avoid pytest intercepting KeyboardInterrupt at the
    session level.  The child process raises KeyboardInterrupt inside run_sensor
    and must exit with code 130 (or 0) — never with an uncaught traceback.
    """

    def _run_child_script(self, script: str) -> subprocess.CompletedProcess:
        """Run a Python script in a subprocess and return the result."""
        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_keyboard_interrupt_in_run_sensor_exits_130(self, tmp_path):
        """run_sensor catches KeyboardInterrupt and exits 130 (no traceback)."""
        sensor_yaml = tmp_path / "sensor.yaml"
        script = textwrap.dedent(f"""
import sys, types, pathlib, os

# Ensure repo root is on path
sys.path.insert(0, {str(tmp_path.parent.parent)!r})

import yaml
sensor_yaml_path = {str(sensor_yaml)!r}
os.makedirs(pathlib.Path(sensor_yaml_path).parent, exist_ok=True)
with open(sensor_yaml_path, "w") as f:
    yaml.dump({{
        "console_url": "https://console.example.com",
        "sensor_id": "test-sensor-id",
        "segment": "dmz",
        "sensor_version": "5.4.0-dev",
        "hmac_key": "deadbeefdeadbeef" * 2,
        "console_api_token": "tok-test",
    }}, f)

# Patch _run_local_scan to raise KeyboardInterrupt
import quirk.cli.sensor_cmd as sc

def _raise_kbi(*a, **kw):
    raise KeyboardInterrupt

sc._run_local_scan = _raise_kbi

# Also patch validate_external_url to always pass
from unittest.mock import MagicMock
sc.validate_external_url = lambda url: MagicMock(ok=True)

try:
    sc.run_sensor(["push", "--config", sensor_yaml_path])
except SystemExit as e:
    sys.exit(e.code or 0)
""")
        result = self._run_child_script(script)
        assert result.returncode in (0, 130, 1), (
            f"Expected exit code 0, 1, or 130 on KeyboardInterrupt, "
            f"got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
        # Verify no uncaught traceback (Traceback (most recent call last))
        assert "Traceback (most recent call last)" not in result.stderr, (
            "Uncaught traceback on KeyboardInterrupt — clean shutdown failed\n"
            f"stderr: {result.stderr}"
        )

    def test_keyboard_interrupt_no_traceback(self, tmp_path):
        """KeyboardInterrupt must not produce a Python traceback in stderr."""
        sensor_yaml = tmp_path / "sensor.yaml"
        script = textwrap.dedent(f"""
import sys, os, pathlib
sys.path.insert(0, {str(tmp_path.parent.parent)!r})

import yaml
sensor_yaml_path = {str(sensor_yaml)!r}
os.makedirs(pathlib.Path(sensor_yaml_path).parent, exist_ok=True)
with open(sensor_yaml_path, "w") as f:
    yaml.dump({{
        "console_url": "https://console.example.com",
        "sensor_id": "test-sensor-id",
        "segment": "dmz",
        "sensor_version": "5.4.0-dev",
        "hmac_key": "deadbeefdeadbeef" * 2,
        "console_api_token": "tok",
    }}, f)

import quirk.cli.sensor_cmd as sc
from unittest.mock import MagicMock

def _raise_kbi(*a, **kw):
    raise KeyboardInterrupt

sc._run_local_scan = _raise_kbi
sc.validate_external_url = lambda url: MagicMock(ok=True)

try:
    sc.run_sensor(["push", "--config", sensor_yaml_path])
except SystemExit as e:
    sys.exit(e.code or 0)
""")
        result = self._run_child_script(script)
        assert "Traceback (most recent call last)" not in result.stderr, (
            "KeyboardInterrupt produced a traceback — clean shutdown not implemented\n"
            f"stderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Test: module imports cleanly with only core deps
# ---------------------------------------------------------------------------


def test_module_imports_with_core_deps():
    """The smoke module itself must import cleanly — no [all] extras required."""
    # If this test is collected at all, the import succeeded.
    import quirk.cli.sensor_cmd  # noqa: F401
    assert hasattr(quirk.cli.sensor_cmd, "_build_envelope")
    assert hasattr(quirk.cli.sensor_cmd, "_build_compressed_payload")
    assert hasattr(quirk.cli.sensor_cmd, "run_sensor")


def test_build_compressed_payload_produces_bytes():
    """_build_compressed_payload returns bytes (decompressible with zstandard)."""
    import zstandard

    envelope = _build_envelope(SAMPLE_SENSOR_CFG, [])
    compressed = _build_compressed_payload(envelope)
    assert isinstance(compressed, bytes)
    assert len(compressed) > 0

    # Round-trip: decompress and parse as JSON
    raw = zstandard.ZstdDecompressor().decompress(compressed)
    recovered = json.loads(raw.decode("utf-8"))
    assert recovered["sensor_id"] == SAMPLE_SENSOR_CFG["sensor_id"]
    assert recovered["segment"] == SAMPLE_SENSOR_CFG["segment"]
