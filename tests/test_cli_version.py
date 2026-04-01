"""Phase 7 — BRAND-02: CLI --version flag test."""
import subprocess
import sys
import re


def test_version_flag():
    """quirk --version must output 'QU.I.R.K. v{version}' to stdout."""
    result = subprocess.run(
        [sys.executable, "run_scan.py", "--version"],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert re.search(r"QU\.I\.R\.K\. v\d+\.\d+\.\d+", output), (
        f"Expected 'QU.I.R.K. vX.Y.Z' in output, got: {output!r}"
    )
