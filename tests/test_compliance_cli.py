"""Phase 49 COMPLY-08 smoke: ``quirk compliance status`` exits 0 and prints
the three frameworks; ``--format json`` produces parseable JSON.

RED-state baseline: this test is expected to fail until Plan 49-03 wires the
CLI subcommand into ``run_scan.py``. Wave 0 only proves the test is collectable.
"""
from __future__ import annotations

import json
import pathlib

from tests.cli_helpers import run_cli

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_run_scan_path_exists():
    """Catch accidental rename of run_scan.py entrypoint."""
    entry = _REPO_ROOT / "run_scan.py"
    assert entry.is_file(), (
        f"CLI entrypoint missing at {entry}. Update test if file was renamed."
    )


def test_status_text_smoke():
    result = run_cli(["compliance", "status"], timeout=30)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    for needle in ("PCI-DSS", "HIPAA", "FIPS"):
        assert needle in result.stdout, (
            f"`compliance status` output missing '{needle}': {result.stdout}"
        )


def test_status_json_smoke():
    result = run_cli(["compliance", "status", "--format", "json"], timeout=30)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
    assert any(
        "PCI" in k or "HIPAA" in k or "FIPS" in k for k in data.keys()
    ), f"JSON keys missing framework names: {list(data.keys())}"
