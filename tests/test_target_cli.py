"""Phase 164 FIRSTRUN-02 / D-01 / D-09 / D-13: --targets CLI-boundary tests.

Covers the two structural fixes that make the --targets abbreviation
traceback impossible:

- D-01/D-02: allow_abbrev=False on every ArgumentParser/add_parser
  construction in run_scan.py, so no flag anywhere in the CLI can be
  matched by an unambiguous prefix.
- D-07/D-08/D-09: --targets-file failures (missing path, malformed
  target/CIDR token) are caught at the CLI boundary and emit coded,
  exit-2 [QRK-TARGET-00N] messages instead of an uncaught traceback,
  and the missing-path case fails before the banner/wizard ever run.

D-13 constraint: the interactive config wizard is never driven with
piped stdin in this module. Every test here either fails before the
wizard starts (parser rejection, missing --targets-file) or supplies
--config so the wizard is never entered.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_SCAN = REPO_ROOT / "run_scan.py"

# Distinctive, stable literal from quirk/cli/banner.py's print_banner() body.
# Used to assert the startup banner did NOT print (proves early-exit ordering).
BANNER_LITERAL = "Quantum Infrastructure Readiness Kit"


def test_targets_flag_rejected_by_parser():
    """--targets is not a real flag; allow_abbrev=False rejects the prefix match."""
    result = subprocess.run(
        [sys.executable, str(RUN_SCAN), "--targets", "127.0.0.1"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=20,
    )
    assert result.returncode == 2, (
        f"Expected exit 2, got {result.returncode}. stderr={result.stderr!r}"
    )
    assert "unrecognized arguments" in result.stderr, (
        f"Expected 'unrecognized arguments' in stderr, got: {result.stderr!r}"
    )


def test_targets_flag_rejection_precedes_wizard_and_banner():
    """The --targets rejection must never reach the wizard or crash with a traceback."""
    result = subprocess.run(
        [sys.executable, str(RUN_SCAN), "--targets", "127.0.0.1"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=20,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    for forbidden in ("Config captured.", "Traceback", "FileNotFoundError"):
        assert forbidden not in combined, (
            f"Unexpected {forbidden!r} in combined output: {combined!r}"
        )


def test_all_parsers_disable_abbrev():
    """All 10 ArgumentParser/add_parser sites in run_scan.py set allow_abbrev=False.

    Corrected site inventory (CONTEXT.md's D-02 said six; direct inspection
    found ten): 5 literal ArgumentParser(...) constructors (init, serve,
    compliance, db, main) + 5 add_parser(...) sub-parser calls (compliance
    status, compliance cmvp, cmvp refresh, cmvp status, db migrate).
    """
    import run_scan

    src = inspect.getsource(run_scan)
    count = src.count("allow_abbrev=False")
    assert count == 10, (
        f"Expected 10 allow_abbrev=False sites (5 ArgumentParser() + "
        f"5 add_parser()), found {count}. If you added a new parser "
        f"construction, give it allow_abbrev=False too (D-02)."
    )


def test_subcommand_flag_abbreviation_rejected():
    """A sub-parser's flag abbreviation is also rejected -- proves add_parser
    forwards allow_abbrev=False through to the underlying ArgumentParser."""
    result = subprocess.run(
        [sys.executable, str(RUN_SCAN), "compliance", "status", "--form", "json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=20,
    )
    assert result.returncode == 2, (
        f"Expected exit 2, got {result.returncode}. stderr={result.stderr!r}"
    )
    assert "unrecognized arguments" in result.stderr, (
        f"Expected 'unrecognized arguments' in stderr, got: {result.stderr!r}"
    )


def test_missing_targets_file_emits_target_001_exit_2():
    """A nonexistent --targets-file path emits [QRK-TARGET-001] and exits 2."""
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_SCAN),
            "--targets-file",
            "/nonexistent/quirk-164-missing.txt",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=20,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 2, (
        f"Expected exit 2, got {result.returncode}. combined={combined!r}"
    )
    assert "QRK-TARGET-001" in combined, (
        f"Expected QRK-TARGET-001 in output; got: {combined!r}"
    )


def test_missing_targets_file_fails_before_wizard():
    """The missing-targets-file guard fires before the banner/wizard (D-09)."""
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_SCAN),
            "--targets-file",
            "/nonexistent/quirk-164-missing.txt",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=20,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    for forbidden in ("Config captured.", "Traceback"):
        assert forbidden not in combined, (
            f"Unexpected {forbidden!r} in combined output: {combined!r}"
        )
    assert BANNER_LITERAL not in combined, (
        f"Startup banner printed before the TARGET-001 guard fired: {combined!r}"
    )


def test_malformed_target_token_emits_target_002_exit_2(tmp_path):
    """A malformed CIDR in a --targets-file emits [QRK-TARGET-002] and exits 2.

    Uses `quirk init` to generate a minimal valid config so the run reaches
    the apply_targets_file_override() call site instead of the wizard,
    honoring D-13 (no piped-stdin wizard driving).
    """
    init_result = subprocess.run(
        [sys.executable, str(RUN_SCAN), "init", "--output", "config.yaml"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=20,
    )
    assert init_result.returncode == 0, (
        f"quirk init failed: stdout={init_result.stdout!r} "
        f"stderr={init_result.stderr!r}"
    )
    config_path = tmp_path / "config.yaml"
    assert config_path.exists(), "quirk init did not create config.yaml"

    targets_file = tmp_path / "bad_targets.txt"
    targets_file.write_text("10.0.0.0/99\n")

    result = subprocess.run(
        [
            sys.executable,
            str(RUN_SCAN),
            "--config",
            "config.yaml",
            "--targets-file",
            str(targets_file),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=20,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 2, (
        f"Expected exit 2, got {result.returncode}. combined={combined!r}"
    )
    assert "QRK-TARGET-002" in combined, (
        f"Expected QRK-TARGET-002 in output; got: {combined!r}"
    )
    assert "Traceback" not in combined, f"Unexpected traceback: {combined!r}"


def test_directory_as_targets_file_emits_target_003_exit_2(tmp_path):
    """A directory passed to --targets-file exits 2 coded, never a traceback.

    Regression pin for code-review WR-01. os.path.exists() returns True for a
    directory, so the D-09 guard used to wave this through to open(), which
    raises IsADirectoryError -- an OSError sibling of FileNotFoundError that
    no except clause caught. The user got a raw traceback, the exact defect
    class FIRSTRUN-02 forbids.
    """
    a_dir = tmp_path / "not_a_file"
    a_dir.mkdir()
    result = subprocess.run(
        [sys.executable, str(RUN_SCAN), "--targets-file", str(a_dir)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=20,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 2, (
        f"Expected exit 2, got {result.returncode}. combined={combined!r}"
    )
    assert "QRK-TARGET-003" in combined, (
        f"Expected QRK-TARGET-003 in output; got: {combined!r}"
    )
    assert "Traceback" not in combined, f"Traceback leaked: {combined!r}"
    assert BANNER_LITERAL not in combined, (
        f"Banner printed before the TARGET-003 guard fired: {combined!r}"
    )


def test_unreadable_targets_file_emits_target_003_exit_2(tmp_path):
    """An existing but unreadable --targets-file exits 2 coded (WR-02).

    PermissionError is likewise an OSError sibling of FileNotFoundError.
    Skipped when running as root, where the mode bits do not deny access.
    """
    import os

    if os.geteuid() == 0:
        import pytest

        pytest.skip("root bypasses the mode bits this test relies on")

    unreadable = tmp_path / "noperm.txt"
    unreadable.write_text("127.0.0.1\n", encoding="utf-8")
    unreadable.chmod(0o000)
    try:
        result = subprocess.run(
            [sys.executable, str(RUN_SCAN), "--targets-file", str(unreadable)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=20,
        )
    finally:
        unreadable.chmod(0o644)
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 2, (
        f"Expected exit 2, got {result.returncode}. combined={combined!r}"
    )
    assert "QRK-TARGET-003" in combined, (
        f"Expected QRK-TARGET-003 in output; got: {combined!r}"
    )
    assert "Traceback" not in combined, f"Traceback leaked: {combined!r}"
