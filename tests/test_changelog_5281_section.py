"""Content gate for the hand-composed ``## [5.28.1]`` CHANGELOG section (Phase 235.1-12, REL-08).

``release.yml`` publishes this section as the public release body and fails closed
when it is missing. The date is a Phase 235.2 concern (reset at tag time), so only
its ISO shape is asserted. Reads CHANGELOG.md only; never touches ``.planning/``.
"""
from __future__ import annotations

import re
from pathlib import Path

_CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
_HEADING = re.compile(r"^## \[5\.28\.1\] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)
_INTERNAL_IDS = re.compile(
    r"999\.|\.planning|\b261\d{3}-|\bD-\d{2}\b|\bCR-0\d\b|\bWR-\d{2}\b"
)


def _text() -> str:
    return _CHANGELOG.read_text(encoding="utf-8")


def _section(version: str) -> str:
    text = _text()
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n", text, re.MULTILINE)
    assert m, f"CHANGELOG.md has no '## [{version}]' section"
    nxt = re.search(r"^## \[", text[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[m.end():end]


def _s() -> str:
    return _section("5.28.1")


def test_heading_dated_and_above_5280() -> None:
    text = _text()
    m = _HEADING.search(text)
    assert m, "missing '## [5.28.1] - YYYY-MM-DD' heading"
    old = re.search(r"^## \[5\.28\.0\]", text, re.MULTILINE)
    assert old and m.start() < old.start(), "[5.28.1] must sit above [5.28.0]"


def test_unreleased_stays_empty() -> None:
    text = _text()
    body = text.split("## [Unreleased]", 1)[1].split("## [5.28.1]", 1)[0]
    assert body.strip() == "", "[Unreleased] must stay empty"


def test_python_315_unsupported_and_yank_and_pin() -> None:
    s = _s()
    assert "3.15" in s and re.search(r"not supported|unsupported", s, re.I), (
        "must say Python 3.15 is not supported"
    )
    assert "4.10.0" in s and "5.21.0" in s and re.search(r"yank", s, re.I), (
        "must name the 4.10.0 to 5.21.0 range and the yank"
    )
    assert "==" in s, "must give an exact == pin example"


def test_missing_binary_fix_and_score_effect() -> None:
    s = _s()
    assert "semgrep" in s and "syft" in s, "must name semgrep and syft"
    assert re.search(r"missing-binary|Not assessed", s), (
        "must say the domain reads Not assessed / missing-binary"
    )
    assert "about 1 to 2 points" in re.sub(r"\s+", " ", s), "must state the score effect"


def test_source_scan_isolation_disclosed() -> None:
    s = re.sub(r"\s+", " ", _s())
    assert re.search(r"keeps? (the )?results (from|of) repositories that succeeded", s), (
        "must say results from succeeded repositories are kept"
    )
    assert re.search(r"each failed repository .{0,60}scan error", s), (
        "must say each failed repository is its own scan error"
    )
    assert re.search(r"can score differently", s), (
        "must say a partly failing source scan can score differently"
    )


def test_doctor_changes() -> None:
    s = _s()
    assert "quirk doctor" in s
    assert "3.10" in s and "3.14" in s
    assert "QUIRK_DB_PATH" in s or "database path" in s


def test_release_check_fixes_mentioned() -> None:
    assert re.search(r"release smoke", _s(), re.I), "must mention the release smoke fixes"


def test_no_internal_ids() -> None:
    hits = _INTERNAL_IDS.findall(_s())
    assert not hits, f"internal ids leaked into release notes: {hits}"


def test_5280_known_defect_names_both_semgrep_cases() -> None:
    s = _section("5.28.0")
    assert "ruleset unavailable" in s
    flat = re.sub(r"\s+", " ", s)
    assert re.search(r"semgrep not installed", flat, re.I) or (
        "semgrep" in flat and "not installed" in flat
    ), "5.28.0 known defects must name the semgrep-not-installed case"
    assert "fixed in 5.28.1" in flat


def test_known_defects_carried_forward() -> None:
    assert re.search(r"known defects", _s(), re.I)
