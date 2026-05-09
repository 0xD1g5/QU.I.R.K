"""Tests for Phase 57 / CR-03 / HARDEN-SCAN-04: container_scanner argv-injection guard."""
from unittest.mock import patch, MagicMock
import pytest

from quirk.scanner.container_scanner import scan_container_image


@pytest.mark.parametrize("bad_ref,expected_reason", [
    ("dir:/", "invalid_image_ref"),
    ("file:///etc/passwd", "invalid_image_ref"),
    ("-q --output=evil", "leading_dash"),
    ("--from=oci-archive", "leading_dash"),
    ("alpine; rm -rf /", "shell_metachar"),
    ("alpine`whoami`", "shell_metachar"),
    ("alpine$(id)", "shell_metachar"),
    ("", "invalid_image_ref"),
])
def test_rejects_malicious_image_ref_no_subprocess(bad_ref, expected_reason):
    with patch("subprocess.run") as mock_run, \
         patch("shutil.which", return_value="/usr/bin/syft"):
        endpoints = scan_container_image(bad_ref, timeout=120)
        mock_run.assert_not_called()
        assert len(endpoints) == 1
        ep = endpoints[0]
        assert ep.protocol == "CONTAINER"
        assert ep.scan_error_category == "invalid_input"
        assert ep.scan_error == expected_reason
        assert len(ep.host) <= 32


def test_valid_image_ref_uses_argv_terminator():
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = '{"artifacts": []}'
    proc.stderr = ""
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=proc) as mock_run:
        scan_container_image("alpine:latest", timeout=120)
        assert mock_run.call_count == 1
        argv = mock_run.call_args.args[0]
        assert "--" in argv
        assert argv[-2] == "--"
        assert argv[-1] == "alpine:latest"


def test_registry_image_passes():
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = '{"artifacts": []}'
    proc.stderr = ""
    with patch("shutil.which", return_value="/usr/bin/syft"), \
         patch("subprocess.run", return_value=proc) as mock_run:
        scan_container_image("ghcr.io/org/repo:1.2.3", timeout=120)
        mock_run.assert_called_once()
