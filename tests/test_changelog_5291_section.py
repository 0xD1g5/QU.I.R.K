"""Content gate for the hand-composed ``## [5.29.1]`` CHANGELOG section (Phase 240 plan 15).

``release.yml`` publishes this section as the public release body. The date is reset at tag time, so only its
ISO shape is asserted. GHSA ids are banned along with internal ids. Reads CHANGELOG.md only; never touches
``.planning/``.
"""
from __future__ import annotations

import re
from pathlib import Path

_CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
_HEADING = re.compile(r"^## \[5\.29\.1\] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)
_INTERNAL_IDS = re.compile(
    r"999\.|\.planning|\b26\d{4}-|\bD-\d{2}\b|\bCR-0\d\b|\bWR-\d{2}\b|\bP-\d{2}\b|GHSA-"
)


def _text() -> str:
    return _CHANGELOG.read_text(encoding="utf-8")


def _s() -> str:
    text = _text()
    m = re.search(r"^## \[5\.29\.1\][^\n]*\n", text, re.MULTILINE)
    assert m, "CHANGELOG.md has no '## [5.29.1]' section"
    nxt = re.search(r"^## \[", text[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[m.end():end]


def test_heading_dated_and_above_5290() -> None:
    text = _text()
    m = _HEADING.search(text)
    assert m, "missing '## [5.29.1] - YYYY-MM-DD' heading"
    old = re.search(r"^## \[5\.29\.0\]", text, re.MULTILINE)
    assert old and m.start() < old.start(), "[5.29.1] must sit above [5.29.0]"


def test_unreleased_stays_empty() -> None:
    text = _text()
    i = text.index("## [Unreleased]") + len("## [Unreleased]")
    nxt = re.search(r"^## \[", text[i:], re.MULTILINE)
    assert nxt, "no release heading after [Unreleased]"
    assert text[i:i + nxt.start()].strip() == "", "[Unreleased] must stay empty"


def test_fixed_block_names_both_changes() -> None:
    s = re.sub(r"\s+", " ", _s())
    assert "### Fixed" in s
    for term in ("PDF browser driver", "HTML and data reports", "libatomic1"):
        assert term in s, f"5.29.1 section must mention {term!r}"


def test_no_internal_or_advisory_ids() -> None:
    hits = _INTERNAL_IDS.findall(_s())
    assert not hits, f"internal or advisory ids leaked into release notes: {hits}"
