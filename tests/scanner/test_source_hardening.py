"""Tests for Phase 57 / CR-02 / HARDEN-SCAN-03: source_scanner argv-injection guard."""
from unittest.mock import patch, MagicMock
import pytest

from quirk.scanner.source_scanner import scan_source_repo


@pytest.mark.parametrize("bad_path,expected_reason", [
    ("../../etc/passwd", "path_traversal"),
    ("/tmp/x; rm -rf /", "shell_metachar"),
    ("/tmp/$(whoami)", "shell_metachar"),
    ("--config=https://evil/rules.yml", "leading_dash"),
    ("-config=evil", "leading_dash"),
    ("", "path_traversal"),
])
def test_rejects_malicious_repo_path_no_subprocess(bad_path, expected_reason):
    with patch("subprocess.run") as mock_run, \
         patch("shutil.which", return_value="/usr/bin/semgrep"):
        endpoints = scan_source_repo(bad_path, timeout=120)
        mock_run.assert_not_called()
        assert len(endpoints) == 1
        ep = endpoints[0]
        assert ep.protocol == "SOURCE"
        assert ep.scan_error_category == "invalid_input"
        assert ep.scan_error == expected_reason
        assert len(ep.host) <= 32  # D-08 redacted preview length cap


def test_rejects_nonexistent_path():
    with patch("subprocess.run") as mock_run, \
         patch("shutil.which", return_value="/usr/bin/semgrep"):
        endpoints = scan_source_repo("/no/such/path/abc123xyz", timeout=120)
        mock_run.assert_not_called()
        assert endpoints[0].scan_error == "nonexistent_path"


def test_valid_path_uses_argv_terminator(tmp_path):
    # Create a real directory so validate_repo_path passes
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = '{"results": []}'
    proc.stderr = ""
    with patch("shutil.which", return_value="/usr/bin/semgrep"), \
         patch("subprocess.run", return_value=proc) as mock_run:
        scan_source_repo(str(tmp_path), timeout=120)
        assert mock_run.call_count == 1
        argv = mock_run.call_args.args[0]
        assert "--" in argv
        # `--` must appear immediately before the repo_path (last positional)
        assert argv[-2] == "--"
        assert argv[-1] == str(tmp_path)
