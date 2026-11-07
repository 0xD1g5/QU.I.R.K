"""Tests for container/binary scanner (SCAN-04).

Tests mock subprocess.run to avoid requiring syft binary.
Scanner module: quirk/scanner/container_scanner.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from quirk.scanner.container_scanner import scan_container_image, scan_container_targets

SAMPLE_SYFT_OUTPUT = {
    "artifacts": [
        {"name": "openssl", "version": "3.0.2", "type": "deb", "purl": "pkg:deb/ubuntu/openssl@3.0.2"},
        {"name": "libssl3", "version": "3.0.2", "type": "deb", "purl": "pkg:deb/ubuntu/libssl3@3.0.2"},
        {"name": "curl", "version": "7.81.0", "type": "deb", "purl": "pkg:deb/ubuntu/curl@7.81.0"},
        {"name": "zlib", "version": "1.2.11", "type": "deb", "purl": "pkg:deb/ubuntu/zlib@1.2.11"},
        {"name": "cryptography", "version": "42.0.5", "type": "python", "purl": "pkg:pypi/cryptography@42.0.5"},
    ],
    "source": {"type": "image", "target": {"userInput": "python:3.12-slim"}}
}


def test_syft_not_found():
    """If syft binary is absent, must return empty list (per D-10)."""
    with patch("shutil.which", return_value=None):
        endpoints = scan_container_image("python:3.12-slim", timeout=60)
        assert endpoints == []


def test_allowlist_filter():
    """Only crypto libraries from allowlist must produce CryptoEndpoint rows."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SYFT_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=mock_proc):
        endpoints = scan_container_image("python:3.12-slim", timeout=60)
        # openssl, libssl3, cryptography pass filter; curl, zlib do not
        assert len(endpoints) == 3
        names = {ep.cipher_suite for ep in endpoints}
        assert "openssl" in names
        assert "libssl3" in names
        assert "cryptography" in names
        assert "curl" not in names


def test_container_endpoint_fields():
    """Each container CryptoEndpoint must have correct protocol and fields (per D-09)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SYFT_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=mock_proc):
        endpoints = scan_container_image("python:3.12-slim", timeout=60)
        for ep in endpoints:
            assert ep.protocol == "CONTAINER"
            assert ep.host == "python:3.12-slim"
            assert ep.port == 0
            assert ep.container_scan_json is not None


def test_syft_json_parse_error():
    """Invalid syft output must return empty list, not raise."""
    mock_proc = MagicMock()
    mock_proc.stdout = "not valid json"
    mock_proc.returncode = 1

    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=mock_proc):
        endpoints = scan_container_image("bad-image", timeout=60)
        assert endpoints == []


# --- 235.3 P-15: per-image outcomes -----------------------------------------
import subprocess

from quirk.scanner.target_outcome import (
    TargetOutcomeContractError,
    TargetOutcomes,
)


def _proc(stdout, rc=0):
    p = MagicMock()
    p.stdout = stdout
    p.returncode = rc
    return p


def _run_one(image, proc=None, side_effect=None):
    sink = TargetOutcomes([image])
    kw = {"side_effect": side_effect} if side_effect else {"return_value": proc}
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", **kw):
        rows = scan_container_targets([image], outcomes=sink)
    return rows, sink.resolved()[0]


def test_outcome_answered_with_artifacts():
    rows, o = _run_one("img:1", _proc(json.dumps(SAMPLE_SYFT_OUTPUT)))
    assert o.kind == "answered" and rows


def test_outcome_answered_zero_artifacts():
    rows, o = _run_one("img:1", _proc(json.dumps({"artifacts": []})))
    assert o.kind == "answered" and rows == []


def test_outcome_unreachable_nonzero_exit_non_json():
    rows, o = _run_one("img:1", _proc("boom", rc=1))
    assert o.kind == "unreachable" and rows == [] and not o.row_emitted


def test_outcome_unreachable_timeout():
    rows, o = _run_one("img:1", side_effect=subprocess.TimeoutExpired("syft", 1))
    assert o.kind == "unreachable" and rows == []


def test_outcome_unreachable_when_image_scan_raises():
    sink = TargetOutcomes(["img:1"])
    with patch("quirk.scanner.container_scanner.scan_container_image",
               side_effect=RuntimeError("pull failed")):
        rows = scan_container_targets(["img:1"], outcomes=sink)
    assert rows == []
    o = sink.resolved()[0]
    assert o.kind == "unreachable" and "pull failed" in o.detail


def test_outcome_mixed_two_images():
    sink = TargetOutcomes(["good:1", "bad:1"])
    procs = [_proc(json.dumps({"artifacts": []})), _proc("nope", rc=1)]
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", side_effect=procs):
        scan_container_targets(["good:1", "bad:1"], outcomes=sink)
    assert [o.kind for o in sink.resolved()] == ["answered", "unreachable"]


def test_outcome_credentials_redacted_in_resolved():
    ref = "docker://user:pass@registry.example.com/img:1"
    sink = TargetOutcomes([ref])
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=_proc("x", rc=1)):
        scan_container_targets([ref], outcomes=sink)
    assert "user:pass" not in repr(sink.resolved())


def test_outcome_contract_violation_propagates():
    sink = TargetOutcomes(["not-this-target"])
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=_proc(json.dumps({"artifacts": []}))):
        with pytest.raises(TargetOutcomeContractError):
            scan_container_targets(["img:1"], outcomes=sink)


def test_outcomes_none_unchanged():
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=_proc(json.dumps(SAMPLE_SYFT_OUTPUT))):
        rows = scan_container_targets(["img:1"])
    assert len(rows) == 3
