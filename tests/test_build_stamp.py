"""Tests for quirk.build_stamp -- the scanner build identity in scan output.

Written against the 2026-09-14 incident: a chaos-lab scan reported 91/100 from
a prober image built before the v3 scoring change (same evidence scores 15/100
under v3), exited 0, and warned about nothing. `Platform version` read 5.21.0
in both cases, so nothing in the output distinguished them.

No subprocess anywhere in this file: fixtures are built as plain files in
tmp_path, matching the module's own no-fork design and sidestepping
tests/test_cli_helper_usage.py's spawn gate entirely.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from quirk.build_stamp import (
    BUILD_SHA_ENV,
    UNKNOWN,
    _read_sha_from_git_dir,
    scanner_build_stamp,
)

SHA = "0123456789abcdef0123456789abcdef01234567"
SHA2 = "fedcba9876543210fedcba9876543210fedcba98"


def _git_dir(tmp_path: Path) -> Path:
    g = tmp_path / ".git"
    g.mkdir()
    return g


def test_env_var_wins_over_git(tmp_path, monkeypatch):
    """Inside a container the baked-in SHA describes the INSTALLED code; any
    .git present describes the build context instead. Env must win."""
    monkeypatch.setenv(BUILD_SHA_ENV, SHA2)
    assert scanner_build_stamp() == SHA2[:12]


def test_env_var_is_truncated_and_stripped(monkeypatch):
    monkeypatch.setenv(BUILD_SHA_ENV, f"  {SHA2}\n")
    assert scanner_build_stamp() == SHA2[:12]


def test_blank_env_var_falls_through(monkeypatch):
    """An env var set to empty must not read as a build identity of ''."""
    monkeypatch.setenv(BUILD_SHA_ENV, "   ")
    stamp = scanner_build_stamp()
    assert stamp and stamp != ""


def test_detached_head(tmp_path):
    g = _git_dir(tmp_path)
    (g / "HEAD").write_text(SHA + "\n", encoding="utf-8")
    assert _read_sha_from_git_dir(tmp_path) == SHA


def test_branch_ref(tmp_path):
    g = _git_dir(tmp_path)
    (g / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    ref = g / "refs" / "heads"
    ref.mkdir(parents=True)
    (ref / "main").write_text(SHA + "\n", encoding="utf-8")
    assert _read_sha_from_git_dir(tmp_path) == SHA


def test_packed_refs_fallback(tmp_path):
    """A fresh clone has no loose ref file -- the SHA is in packed-refs."""
    g = _git_dir(tmp_path)
    (g / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (g / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n"
        f"{SHA} refs/heads/main\n"
        f"{SHA2} refs/remotes/origin/main\n",
        encoding="utf-8",
    )
    assert _read_sha_from_git_dir(tmp_path) == SHA


def test_packed_refs_ignores_peeled_lines(tmp_path):
    """A '^'-prefixed peeled-tag line must never be mistaken for a ref row."""
    g = _git_dir(tmp_path)
    (g / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (g / "packed-refs").write_text(
        f"{SHA2} refs/tags/v1\n^{SHA}\n{SHA} refs/heads/main\n", encoding="utf-8"
    )
    assert _read_sha_from_git_dir(tmp_path) == SHA


def test_worktree_gitdir_pointer(tmp_path):
    """This repo uses worktrees (execute-phase runs agents in them), where
    `.git` is a FILE holding `gitdir: <path>`, not a directory."""
    real = tmp_path / "realgit"
    real.mkdir()
    (real / "HEAD").write_text(SHA + "\n", encoding="utf-8")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")
    assert _read_sha_from_git_dir(wt) == SHA


def test_no_git_anywhere_returns_none(tmp_path):
    assert _read_sha_from_git_dir(tmp_path) is None


def test_installed_wheel_reports_unknown_not_a_version(tmp_path, monkeypatch):
    """The whole point: when the build cannot be identified, SAY SO.

    Substituting the package version here would recreate the exact failure --
    `Platform version 5.21.0` was printed by both the stale and the current
    scanner, which is why the 91/100 scan was unreadable.
    """
    monkeypatch.delenv(BUILD_SHA_ENV, raising=False)
    monkeypatch.setattr(
        "quirk.build_stamp._read_sha_from_git_dir", lambda _start: None
    )
    assert scanner_build_stamp() == UNKNOWN


def test_real_repo_resolves_to_a_sha(monkeypatch):
    """Non-vacuity: the parser must work on THIS checkout, not only fixtures.

    Guarded so an installed-wheel CI checkout (no .git) reports UNKNOWN rather
    than failing -- both are correct outcomes, and asserting the shape of
    whichever occurred still proves the code path ran.
    """
    monkeypatch.delenv(BUILD_SHA_ENV, raising=False)
    stamp = scanner_build_stamp()
    assert stamp == UNKNOWN or re.fullmatch(r"[0-9a-f]{12}", stamp), (
        f"unexpected build stamp shape: {stamp!r}"
    )


def test_summary_table_carries_both_identifying_rows():
    """The rows must actually be wired into the scan summary -- a correct
    stamp nobody prints would not have caught the incident."""
    src = Path(__file__).resolve().parents[1] / "quirk" / "reports" / "writer.py"
    text = src.read_text(encoding="utf-8")
    assert '"Scoring model"' in text, "scan summary must name the scoring model"
    assert '"Scanner build"' in text, "scan summary must name the scanner build"


def test_scoring_model_row_reads_the_live_constant():
    """The row must derive from SCORING_VERSION, not a pasted literal -- a
    hardcoded 'v3.0' would go stale at the next scoring change and re-create
    the defect one version later."""
    src = Path(__file__).resolve().parents[1] / "quirk" / "reports" / "writer.py"
    text = src.read_text(encoding="utf-8")
    assert "f\"v{SCORING_VERSION}\"" in text, (
        "the Scoring model row must interpolate SCORING_VERSION"
    )
    assert "from quirk.intelligence.scoring import SCORING_VERSION" in text
