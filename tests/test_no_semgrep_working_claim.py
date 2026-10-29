"""Standing guard: no tracked public doc presents Semgrep source scanning as working.

Phase 235 D-02/D-15. The Semgrep ``p/cryptography`` registry pack no longer
exists (HTTP 404, semgrep exit 7), so 5.28.0 records a "ruleset unavailable"
scan error and the source domain reads Not assessed. What this checks:

* **Scan set.** Git-TRACKED ``*.md`` under README.md, docs and
  quantum-chaos-enterprise-lab, via ``git ls-files`` (never a recursive glob,
  which reaches gitignored trees). Exclusions are listed in ``EXCLUDED``.
* **Flagged line.** Contains ``p/cryptography``, or ``semgrep`` together with
  ``source`` or ``cryptograph`` on the same line (case-insensitive).
* **Accepted.** A line within +/-3 lines contains ``known defect`` or
  ``ruleset unavailable`` (case-insensitive).
* **KV disclosure (D-01).** README keeps the Key Vault known-defect sentence.
* **Floors.** A scan that sees nothing fails rather than passes.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from tests.cli_helpers import run_fork_safe

REPO = Path(__file__).resolve().parent.parent
ROOTS = ("README.md", "docs", "quantum-chaos-enterprise-lab")

EXCLUDED = {
    "docs/UAT-SERIES.md": "test record; dispositions owned by the UAT plan",
    "docs/uat-coverage-gaps.md": "generated from UAT-SERIES.md",
    "docs/error-codes.md": "generated from quirk/errors.py; INSTALL-008 is 'semgrep not found', not a capability claim",
    "CHANGELOG.md": "history, and outside the roots",
}

FLAG_RE = re.compile(r"p/cryptography|(?=.*semgrep)(?=.*(?:source|cryptograph))", re.I)
MARKER_RE = re.compile(r"known defect|ruleset unavailable", re.I)
WINDOW = 3

KV_SENTENCE = "Key Vault key scanning has a known defect and currently records no keys"

# Measured on git ls-files at the RED commit of 235-05 (a8b3d166 base): 61 tracked
# *.md in the scan set, 33 flagged sites. Floors sit a little below.
FILE_FLOOR = 40
SITE_FLOOR = 25


def tracked_md() -> list[Path]:
    git = shutil.which("git") or "/usr/bin/git"
    r = run_fork_safe([git, "-C", str(REPO), "ls-files", "-z", "--", *ROOTS], check=True)
    out = []
    for p in r.stdout.split("\0"):
        if p.endswith(".md") and p not in EXCLUDED:
            out.append(REPO / p)
    return out


def flagged_unmarked(lines: list[str]) -> tuple[list[int], int]:
    """Return (1-based unmarked flagged line numbers, total flagged count)."""
    bad, total = [], 0
    for i, line in enumerate(lines):
        if not FLAG_RE.search(line):
            continue
        total += 1
        lo, hi = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
        # The Key Vault known-defect sentence is about a different connector.
        if not any(MARKER_RE.search(x) and "key vault" not in x.lower() for x in lines[lo:hi]):
            bad.append(i + 1)
    return bad, total


def _scan() -> tuple[dict[str, list[int]], int, int]:
    files = tracked_md()
    offenders: dict[str, list[int]] = {}
    sites = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        bad, total = flagged_unmarked(text.splitlines())
        sites += total
        if bad:
            offenders[f.relative_to(REPO).as_posix()] = bad
    return offenders, len(files), sites


def test_no_doc_presents_p_cryptography_as_working():
    offenders, _, _ = _scan()
    assert not offenders, (
        "Semgrep source scanning presented without a known-defect / "
        f"ruleset-unavailable marker within {WINDOW} lines: {offenders}"
    )


def test_readme_discloses_key_vault_defect():
    assert KV_SENTENCE in (REPO / "README.md").read_text(encoding="utf-8")


def test_guard_scan_is_not_vacuous():
    _, files, sites = _scan()
    assert files >= FILE_FLOOR, f"only {files} files scanned"
    assert sites >= SITE_FLOOR, f"only {sites} flagged sites"


def test_detector_flags_unmarked_claim(tmp_path):
    lines = ["Semgrep `p/cryptography` finds crypto misuse", "other"]
    bad, total = flagged_unmarked(lines)
    assert bad == [1] and total == 1


def test_detector_accepts_marked_claim(tmp_path):
    lines = [
        "Semgrep `p/cryptography` finds crypto misuse",
        "This is a known defect: ruleset unavailable.",
    ]
    bad, total = flagged_unmarked(lines)
    assert bad == [] and total == 1
