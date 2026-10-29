"""Tests for source code scanner (SCAN-05).

Tests mock subprocess.run to avoid requiring semgrep binary.
Scanner module: quirk/scanner/source_scanner.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from quirk.scanner.source_scanner import (
    SourceRulesetUnavailable,
    SourceScanError,
    scan_source_repo,
    scan_source_targets,
)

EXIT7_FIXTURE = Path(__file__).parent / "fixtures" / "semgrep_exit7_p_cryptography.json"


@pytest.fixture
def fake_semgrep(tmp_path, monkeypatch):
    """Install an executable fake ``semgrep`` first on PATH.

    The real ``subprocess.run`` runs against it (no mock), so the genuine
    exit-7 / valid-JSON behaviour of a 404'd ruleset is exercised.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()

    # macOS: a default close_fds=True spawn after Network.framework is loaded by
    # an earlier test in the same pytest process dies with SIGSEGV, so the fake
    # semgrep printed nothing and these tests failed only in the full suite.
    # Keep the REAL subprocess.run, just spawned fork-safely (close_fds=False).
    real_run = subprocess.run

    def _fork_safe_run(*args, **kwargs):
        kwargs.setdefault("close_fds", False)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _fork_safe_run)

    def _install(stdout: str, code: int) -> str:
        exe = bindir / "semgrep"
        exe.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.stdout.write({stdout!r})\n"
            f"sys.exit({code})\n"
        )
        os.chmod(exe, 0o755)
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
        return str(repo)

    return _install

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


def test_semgrep_json_parse_error(fake_semgrep):
    """Invalid semgrep output must raise, never read as a clean repo."""
    repo = fake_semgrep("invalid json", 1)
    with pytest.raises(SourceScanError) as ei:
        scan_source_repo(repo, timeout=120)
    assert str(ei.value).startswith("source scan failed")
    assert not isinstance(ei.value, SourceRulesetUnavailable)


def test_semgrep_exit7_ruleset_404_raises_ruleset_unavailable(fake_semgrep):
    repo = fake_semgrep(EXIT7_FIXTURE.read_text(), 7)
    with pytest.raises(SourceRulesetUnavailable) as ei:
        scan_source_repo(repo, timeout=120)
    msg = str(ei.value)
    assert msg.startswith("ruleset unavailable")
    assert repo not in msg


def test_scan_source_targets_reraises_ruleset_unavailable(fake_semgrep):
    repo = fake_semgrep(EXIT7_FIXTURE.read_text(), 7)
    with pytest.raises(SourceRulesetUnavailable):
        scan_source_targets([repo])


def test_wrapped_phase_records_source_ruleset_failure(fake_semgrep):
    import run_scan

    repo = fake_semgrep(EXIT7_FIXTURE.read_text(), 7)
    recorder = run_scan._PhaseRecorder()
    run_stats = {"timings_sec": {}, "phase_records": recorder}
    error_endpoints: list = []
    result = run_scan._wrapped_phase(
        run_stats,
        "source_scanning",
        "source_scanner",
        lambda: scan_source_targets([repo]),
        error_endpoints,
        MagicMock(),
    )
    assert result is None or result == []
    rows = [r for r in recorder.rows() if r["phase_name"] == "source_scanning"]
    assert len(rows) == 1
    assert rows[0]["reason"] == "failed"
    # _wrapped_phase persists safe_str(exc), which prefixes the class name.
    assert "ruleset unavailable" in rows[0]["detail"]
    assert rows[0]["detail"].startswith("SourceRulesetUnavailable")
    assert len(error_endpoints) == 1
    assert error_endpoints[0].protocol == "ERROR"
    assert error_endpoints[0].scan_error.startswith("ruleset unavailable")


def test_semgrep_warn_level_errors_do_not_fail(fake_semgrep):
    body = dict(SAMPLE_SEMGREP_OUTPUT)
    body["errors"] = [
        {"code": 3, "level": "warn", "type": "PartialParsing", "message": "x"}
    ]
    repo = fake_semgrep(json.dumps(body), 0)
    endpoints = scan_source_repo(repo, timeout=120)
    assert len(endpoints) == 2


def test_semgrep_not_installed_still_returns_empty(tmp_path):
    (tmp_path / "repo").mkdir()
    with patch("shutil.which", return_value=None):
        assert scan_source_repo(str(tmp_path / "repo")) == []
