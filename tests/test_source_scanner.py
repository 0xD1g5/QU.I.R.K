"""Tests for source code scanner (SCAN-05).

Tests mock subprocess.run to avoid requiring semgrep binary.
Scanner module: quirk/scanner/source_scanner.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from quirk.scanner.source_scanner import scan_source_repo, scan_source_targets

SAMPLE_SEMGREP_OUTPUT = {
    "results": [
        {
            "check_id": "python.cryptography.security.insecure-hash-algorithms.insecure-hash-algorithms-md5",
            "path": "app/auth.py",
            "start": {"line": 42, "col": 4},
            "end": {"line": 42, "col": 30},
            "extra": {
                "message": "Use of weak MD5 hash algorithm",
                "severity": "WARNING",
                "metadata": {"confidence": "HIGH"}
            }
        },
        {
            "check_id": "python.cryptography.security.insecure-cipher-algorithm.insecure-cipher-algorithm-des",
            "path": "app/encrypt.py",
            "start": {"line": 10, "col": 1},
            "end": {"line": 10, "col": 45},
            "extra": {
                "message": "Use of insecure DES cipher",
                "severity": "WARNING",
                "metadata": {"confidence": "HIGH"}
            }
        }
    ],
    "errors": [],
    "stats": {"total_time": 1.23}
}


def test_semgrep_not_found():
    """If semgrep binary is absent, must return empty list (per D-14)."""
    with patch("shutil.which", return_value=None), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert endpoints == []


def test_semgrep_findings_parsed():
    """Each semgrep finding must produce one CryptoEndpoint with protocol='SOURCE' (per D-13)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SEMGREP_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert len(endpoints) == 2
        for ep in endpoints:
            assert ep.protocol == "SOURCE"
            assert ep.host == "/path/to/repo"
            assert ep.port == 0
            assert ep.source_scan_json is not None


def test_semgrep_service_detail_format():
    """service_detail must be 'file:line' format (per D-13)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SEMGREP_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert endpoints[0].service_detail == "app/auth.py:42"
        assert endpoints[1].service_detail == "app/encrypt.py:10"


def test_semgrep_cipher_suite_is_rule_id():
    """cipher_suite must hold the semgrep rule_id (per D-13)."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(SAMPLE_SEMGREP_OUTPUT)
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert "insecure-hash-algorithms-md5" in endpoints[0].cipher_suite


def test_semgrep_json_parse_error():
    """Invalid semgrep output must return empty list, not raise."""
    mock_proc = MagicMock()
    mock_proc.stdout = "invalid json"
    mock_proc.returncode = 1

    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("os.path.isdir", return_value=True):
        endpoints = scan_source_repo("/path/to/repo", timeout=120)
        assert endpoints == []
