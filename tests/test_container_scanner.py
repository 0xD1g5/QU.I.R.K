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
