"""Content gate for the hand-composed ``## [5.28.2]`` CHANGELOG section (Phase 235.3-17, COVTRUTH-06).

``release.yml`` publishes this section as the public release body and fails closed
when it is missing. The date is a Phase 235.4 concern (reset at tag time), so only
its ISO shape is asserted. Reads CHANGELOG.md only; never touches ``.planning/``.
"""
from __future__ import annotations

import re
from pathlib import Path

_CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
_HEADING = re.compile(r"^## \[5\.28\.2\] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)
_INTERNAL_IDS = re.compile(
    r"999\.|\.planning|\b261\d{3}-|\bD-\d{2}\b|\bCR-0\d\b|\bWR-\d{2}\b|\bP-\d{2}\b"
)


def _text() -> str:
    return _CHANGELOG.read_text(encoding="utf-8")


def _s() -> str:
    text = _text()
    m = re.search(r"^## \[5\.28\.2\][^\n]*\n", text, re.MULTILINE)
    assert m, "CHANGELOG.md has no '## [5.28.2]' section"
    nxt = re.search(r"^## \[", text[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[m.end():end]


def test_heading_dated_and_above_5281() -> None:
    text = _text()
    m = _HEADING.search(text)
    assert m, "missing '## [5.28.2] - YYYY-MM-DD' heading"
    old = re.search(r"^## \[5\.28\.1\]", text, re.MULTILINE)
    assert old and m.start() < old.start(), "[5.28.2] must sit above [5.28.1]"


def test_unreleased_stays_empty() -> None:
    text = _text()
    i = text.index("## [Unreleased]") + len("## [Unreleased]")
    nxt = re.search(r"^## \[", text[i:], re.MULTILINE)
    assert nxt, "no release heading after [Unreleased]"
    assert text[i:i + nxt.start()].strip() == "", "[Unreleased] must stay empty"


def test_required_terms_present() -> None:
    s = re.sub(r"\s+", " ", _s())
    for term in ("internal-target-refused", "auth-failed", "missing-credentials",
                 "scan error", "Data at Rest", "Scores can go down"):
        assert term in s, f"5.28.2 section must mention {term!r}"


def test_score_effect_is_quoted_and_source_exemption_stated() -> None:
    s = re.sub(r"\s+", " ", _s())
    assert "84 to 81" in s, "must quote the measured score effect"
    assert re.search(r"every target fails is recorded `failed`", s), (
        "must state the source exemption (failed, not skipped)"
    )


def test_no_internal_ids() -> None:
    hits = _INTERNAL_IDS.findall(_s())
    assert not hits, f"internal ids leaked into release notes: {hits}"
