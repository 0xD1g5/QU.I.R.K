"""Phase 68 UX-01: unit/integration tests for quirk/cli/errors_cmd.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from quirk.cli.errors_cmd import (
    _dump_markdown,
    _domain_of,
    _filtered_entries,
    _normalize_code,
)
from quirk.errors import ERROR_REGISTRY

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_dump_md_starts_with_header():
    assert _dump_markdown().startswith("# QU.I.R.K. Error Code Reference")


def test_dump_md_contains_install_section():
    assert "## INSTALL" in _dump_markdown()


def test_dump_md_contains_all_domains():
    md = _dump_markdown()
    domains = sorted({_domain_of(code) for code in ERROR_REGISTRY})
    for d in domains:
        assert f"## {d}" in md, f"Missing domain header: {d}"


def test_dump_md_contains_install_001_row():
    assert "| QRK-INSTALL-001 |" in _dump_markdown()


def test_normalize_code_strips_qrk_prefix():
    assert _normalize_code("QRK-TLS-001") == "TLS-001"
    assert _normalize_code("TLS-001") == "TLS-001"


def test_filtered_entries_respects_domain():
    entries = _filtered_entries("INSTALL")
    assert entries, "Expected INSTALL entries"
    assert all(code.startswith("INSTALL-") for code, _ in entries)


def test_filtered_entries_empty_for_unknown_domain():
    assert _filtered_entries("BOGUS") == []


def test_filtered_entries_case_insensitive_domain():
    assert _filtered_entries("install") == _filtered_entries("INSTALL")


@pytest.mark.slow
def test_lookup_single_known_returns_zero():
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "QRK-INSTALL-001"],
        capture_output=True, text=True, timeout=15, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "QRK-INSTALL-001" in (result.stdout + result.stderr)


@pytest.mark.slow
def test_lookup_single_unknown_exits_nonzero():
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "BOGUS-999"],
        capture_output=True, text=True, timeout=15, cwd=REPO_ROOT,
    )
    assert result.returncode != 0


@pytest.mark.slow
def test_dump_md_subprocess_matches_helper():
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "--dump-md"],
        capture_output=True, text=True, timeout=15, cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    # subprocess stdout has a trailing newline from print()
    assert result.stdout.rstrip("\n") == _dump_markdown().rstrip("\n")


@pytest.mark.slow
def test_domain_filter_subprocess():
    result = subprocess.run(
        [sys.executable, "run_scan.py", "errors", "--domain", "SCHED"],
        capture_output=True, text=True, timeout=15, cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "SCHED-001" in combined
    # INSTALL codes must NOT leak into a domain-filtered listing
    assert "INSTALL-001" not in combined
