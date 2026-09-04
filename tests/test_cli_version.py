"""Phase 7 — BRAND-02: CLI --version flag test."""
import re

import pytest

from tests.cli_helpers import run_cli


@pytest.mark.slow
def test_version_flag():
    """quirk --version must output 'QU.I.R.K. v{version}' to stdout."""
    result = run_cli(["--version"], timeout=30)
    output = result.stdout + result.stderr
    assert re.search(r"QU\.I\.R\.K\. v\d+\.\d+\.\d+", output), (
        f"Expected 'QU.I.R.K. vX.Y.Z' in output, got: {output!r}"
    )
