"""Phase 7 — BRAND-04: quirk init subcommand tests."""
import subprocess
import sys
import os
import tempfile


def test_init_creates_config(tmp_path):
    """quirk init must create a config.yaml in the specified output path."""
    out = str(tmp_path / "config.yaml")
    result = subprocess.run(
        [sys.executable, "run_scan.py", "init", "--output", out],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"quirk init exited {result.returncode}: {result.stderr}"
    assert os.path.exists(out), f"config.yaml not created at {out}"
    content = open(out).read()
    assert "targets:" in content, "Generated config.yaml must contain 'targets:' key"
    assert "127.0.0.1" in content, "Generated config.yaml must default to 127.0.0.1"


def test_init_no_overwrite(tmp_path):
    """quirk init must not silently overwrite an existing config.yaml."""
    out = str(tmp_path / "config.yaml")
    # First run — creates file
    subprocess.run(
        [sys.executable, "run_scan.py", "init", "--output", out],
        capture_output=True, text=True,
    )
    first_mtime = os.path.getmtime(out)
    # Second run — should warn and not overwrite
    result = subprocess.run(
        [sys.executable, "run_scan.py", "init", "--output", out],
        capture_output=True, text=True,
    )
    second_mtime = os.path.getmtime(out)
    output = result.stdout + result.stderr
    assert "already exists" in output.lower() or "not overwriting" in output.lower(), (
        f"Expected overwrite warning, got: {output!r}"
    )
    assert first_mtime == second_mtime, "File was overwritten when it should have been preserved"
