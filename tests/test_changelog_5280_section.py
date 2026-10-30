"""Guard for the hand-composed ``## [5.28.0]`` CHANGELOG section (Phase 235-09, LAUNCH-01).

``release.yml`` turns this section into the public GitHub release body and fails
closed when it is missing. The section must (D-12) say that scores move on
upgrade, which way and why, and (D-16/D-25) disclose the known defects,
including every score-moving dashboard/report divergence, without leaking
internal ids and without claiming the two score surfaces always agree.

The test reads CHANGELOG.md and README.md from disk and never touches
``.planning/`` (gitignored, absent in CI).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from quirk.dashboard.api.finding_title_bridge import (
    SEVERITY_DIVERGENCES,
    UNBRIDGED_DASHBOARD_TITLES,
)
from tests.cli_helpers import run_fork_safe
from tests.pyproject_helpers import pyproject_version

_ROOT = Path(__file__).resolve().parent.parent
_CHANGELOG = _ROOT / "CHANGELOG.md"
_README = _ROOT / "README.md"

# Code-derived score divergences: every key of SEVERITY_DIVERGENCES and
# UNBRIDGED_DASHBOARD_TITLES maps to the user-term phrase the Known defects
# text must contain. The key set must EQUAL the live union, so adding or fixing
# a divergence turns this red until the release notes follow.
_DIVERGENCE_PHRASES: dict[str, str] = {
    "Legacy TLS version: ": "legacy TLS version",
    "Weak cipher suites enabled": "weak cipher suites",
    "Quantum-": "undersized ECDSA",
}

# Todo-derived score divergences: one (item, phrase) pair per row classified
# "score divergence" in the private todo sweep. Derivation script:
# .planning/phases/235-release-launch-gate/235-evidence/derive_divergences.py
# (plans 235-10/11/12 re-check it and re-run phrase_coverage.py). Rows that
# share a cause share a phrase string.
_TODO_DIVERGENCE_PHRASES: tuple[tuple[str, str], ...] = (
    ("container library end-of-life findings are report-only",
     "end-of-life crypto libraries in container images"),
    ("dashboard and report pipelines still diverge: Kerberos weak etype",
     "Kerberos weak-encryption"),
    ("dashboard and report pipelines still diverge: Slack drift score vs Trends",
     "drift notification"),
    ("dashboard and report pipelines still diverge: DNSSEC",
     "DNSSEC"),
    ("default report deriver drops tls_designated_ports",
     "TLS-designated ports"),
)

# Number of todo-derived score-divergence rows at 235-09; source is
# 235-evidence/phrase_coverage.py (its `rows=` count). The tuple above may grow
# but must never silently shrink below this.
_TODO_SCORE_DIVERGENCE_ROWS = 5

_PARITY = re.compile(
    r"derived the same|same way|identically|same headline|same score|same readiness"
    r"|(same|identical)\b.{0,40}\b(score|headline|ceiling|subscore)",
    re.IGNORECASE,
)
_QUALIFIERS = ("known defect", "can still differ", "still differ", "except")


def _target_version() -> str:
    v = pyproject_version()
    if v.startswith("5.28."):
        return v
    if v == "5.27.0":
        return "5.28.0"  # 235-10 bumps pyproject after this plan
    pytest.fail(
        f"pyproject says {v}: this test pins the 5.28.x release notes; "
        "retire or update it for the new release"
    )


def _text() -> str:
    return _CHANGELOG.read_text(encoding="utf-8")


def _section() -> str:
    text = _text()
    m = re.search(rf"^## \[{re.escape(_target_version())}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$",
                  text, re.M)
    assert m, f"CHANGELOG.md has no '## [{_target_version()}] - YYYY-MM-DD' heading"
    rest = text[m.end():]
    nxt = re.search(r"^## \[", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _known_defects() -> str:
    sec = _section()
    i = sec.find("**Known defects in")
    assert i >= 0, "section has no '**Known defects in' block"
    rest = sec[i:]
    nxt = re.search(r"^### ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def _parity_violations(text: str) -> list[str]:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if not _PARITY.search(line):
            continue
        near = [line]
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j >= 0:
            near.append(lines[j])
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines):
            near.append(lines[j])
        if not any(q in " ".join(near).lower() for q in _QUALIFIERS):
            out.append(line)
    return out


def test_section_order():
    text = _text()
    v = _target_version()
    a = text.index("## [Unreleased]")
    m = re.search(rf"^## \[{re.escape(v)}\] - \d{{4}}-\d{{2}}-\d{{2}}", text, re.M)
    assert m, "missing version heading"
    c = text.index("## [5.27.0] - ")
    assert a < m.start() < c


def test_unreleased_is_empty():
    text = _text()
    i = text.index("## [Unreleased]") + len("## [Unreleased]")
    nxt = text.index("## [", i)
    assert text[i:nxt].strip() == ""


def test_upgrade_notes_content():
    sec = _section()
    for needle in ("**Upgrade notes:**", "SCORING_VERSION", "4.0", "N_REF", "classical",
                   "QRAMM", "docs/report-interpretation.md"):
        assert needle in sec, needle


def test_known_defects_disclosed():
    sec = _section()
    assert "ruleset unavailable" in sec
    assert "Key Vault" in sec
    kd = _known_defects()
    ok = [ln for ln in kd.splitlines()
          if "dashboard" in ln.lower() and "report" in ln.lower()
          and re.search(r"differ|disagree", ln, re.I)]
    assert ok, "Known defects must say the dashboard and report can still differ"


def test_code_divergences_disclosed():
    live = set(SEVERITY_DIVERGENCES) | set(UNBRIDGED_DASHBOARD_TITLES)
    assert set(_DIVERGENCE_PHRASES) == live
    kd = " ".join(_known_defects().lower().split())  # hard-wrap tolerant
    for key, phrase in _DIVERGENCE_PHRASES.items():
        assert phrase.strip(), key
        assert phrase.lower() in kd, (key, phrase)


def test_todo_divergences_disclosed():
    kd = " ".join(_known_defects().lower().split())  # hard-wrap tolerant
    for item, phrase in _TODO_DIVERGENCE_PHRASES:
        assert phrase.strip(), item
        assert phrase.lower() in kd, (item, phrase)


def test_todo_divergence_row_count():
    assert _TODO_SCORE_DIVERGENCE_ROWS >= 1
    assert len(_TODO_DIVERGENCE_PHRASES) >= _TODO_SCORE_DIVERGENCE_ROWS


def test_no_unqualified_parity_claim():
    assert _parity_violations(_section()) == []


def test_readme_no_unqualified_parity_claim():
    assert _parity_violations(_README.read_text(encoding="utf-8")) == []


def test_readme_whats_new_discloses_divergences():
    """README What's New and the CHANGELOG disclose the same divergence phrases (235-10)."""
    text = _README.read_text(encoding="utf-8")
    m = re.search(r"^## What's New in v5\.28\s*$", text, re.M)
    assert m, "README.md has no \"## What's New in v5.28\" heading"
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    sec = (rest[: nxt.start()] if nxt else rest).lower()
    phrases = list(_DIVERGENCE_PHRASES.values()) + [p for _, p in _TODO_DIVERGENCE_PHRASES]
    missing = [p for p in phrases if p.lower() not in sec]
    assert not missing, f"README What's New v5.28 omits divergence phrases: {missing}"


def test_parity_detector_self_test():
    bad1 = "TLS and mail findings are now derived the same way on the dashboard and in the report"
    bad2 = "Both surfaces compute the same headline"
    ok = ("Both surfaces compute scores.\n"
          "Known defect: the dashboard and the report can still differ for legacy TLS.")
    assert _parity_violations(bad1) == [bad1]
    assert _parity_violations(bad2) == [bad2]
    assert _parity_violations("The same headline is shown.\n"
                              "Known defect: the dashboard and the report can still differ.") == []
    assert _parity_violations(ok) == []


def test_no_stale_or_internal_text():
    sec = _section()
    for banned in ("stays 3.0", "999.", ".planning", "embargo"):
        assert banned not in sec, banned
    assert not re.search(r"261\d{3}-", sec)


def test_fragments_consumed():
    res = run_fork_safe([shutil.which("git") or "/usr/bin/git", "-C", str(_ROOT), "ls-files", "changelog.d"])
    files = [f for f in res.stdout.split() if f]
    assert files == ["changelog.d/README.md"], files
