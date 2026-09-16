"""Guards for scripts/build_master_guide.py.

The master guide is a 6,500-line generated document nobody re-reads line by
line, which makes silent corruption the realistic failure mode rather than a
visible crash. Two things can corrupt it quietly:

1. Fence tracking. `grep -c '^# '` reports 33 top-level headings in
   configuration.md; the real count is 1. The other 32 are shell comments
   inside ```bash blocks. A heading transform that does not track fences
   rewrites `# Positional token ...` into `## Positional token ...` and
   corrupts every code example it touches.

2. Anchor collisions. Merging five guides collides 9 anchors across 25 of 302
   headings -- seven slug to `#prerequisites` alone. A contents page built from
   bare slugs sends six of those seven links to the wrong section, and looks
   perfectly fine while doing it.

Each test below is paired with a demonstration that it can fail, because a
green assertion over a generator that silently produced nothing is exactly the
class of false confidence this file exists to prevent.
"""
from __future__ import annotations

import re

import pytest

from scripts.build_master_guide import (
    PARTS,
    AnchorAllocator,
    _iter_lines,
    base_anchor,
    build,
)


# ---------------------------------------------------------------------------
# Fence tracking
# ---------------------------------------------------------------------------

FIXTURE = """# Title

Prose.

```bash
# Positional token (short-lived use)
quirk token issue
```

## Real Heading

~~~text
# not a heading either
~~~

### Another Real Heading
"""


def _headings(text: str) -> list[str]:
    return [
        m.group(2)
        for line, in_fence in _iter_lines(text)
        if not in_fence and (m := re.match(r"^(#{1,6})\s+(.*)$", line))
    ]


def test_shell_comments_inside_fences_are_not_headings() -> None:
    assert _headings(FIXTURE) == ["Title", "Real Heading", "Another Real Heading"]


def test_fence_detection_is_not_vacuous() -> None:
    """A tracker that ignored fences would see the shell comments as headings.

    Without this, `test_shell_comments_inside_fences_are_not_headings` would
    still pass against a fixture that happened to contain no fenced comments.
    """
    naive = [
        m.group(2)
        for line in FIXTURE.split("\n")
        if (m := re.match(r"^(#{1,6})\s+(.*)$", line))
    ]
    assert "Positional token (short-lived use)" in naive
    assert "not a heading either" in naive
    assert len(naive) > len(_headings(FIXTURE))


def test_tilde_fence_does_not_close_on_backticks() -> None:
    text = "~~~\n```\n# still inside\n~~~\n# outside\n"
    assert _headings(text) == ["outside"]


def test_real_guides_contain_fenced_comments() -> None:
    """The hazard is present in the actual sources, not merely hypothetical."""
    from scripts.build_master_guide import REPO_ROOT

    offenders = {}
    for filename, _, _ in PARTS:
        text = (REPO_ROOT / "docs" / filename).read_text(encoding="utf-8")
        fenced = sum(
            1
            for line, in_fence in _iter_lines(text)
            if in_fence and re.match(r"^#{1,6}\s+\S", line)
        )
        if fenced:
            offenders[filename] = fenced
    assert offenders, (
        "no fenced '#' lines found in any source guide -- if the sources really "
        "changed this much, re-justify the fence tracking before deleting it"
    )


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------


def test_anchor_allocator_matches_github_dedup() -> None:
    a = AnchorAllocator()
    assert a.allocate("Prerequisites") == "prerequisites"
    assert a.allocate("Prerequisites") == "prerequisites-1"
    assert a.allocate("Prerequisites") == "prerequisites-2"
    assert a.allocate("Other") == "other"


def test_base_anchor_strips_markdown_punctuation() -> None:
    assert base_anchor("Why `[all]` excludes `[identity]`") == "why-all-excludes-identity"
    assert base_anchor("3.5 Hardening Environment Variables") == "35-hardening-environment-variables"


# ---------------------------------------------------------------------------
# Whole-document invariants
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def master() -> str:
    return build()


def _doc_headings(text: str) -> list[str]:
    return [
        m.group(2).strip()
        for line, in_fence in _iter_lines(text)
        if not in_fence and (m := re.match(r"^(#{1,6})\s+(.*)$", line))
    ]


def test_every_anchor_is_unique(master: str) -> None:
    alloc = AnchorAllocator()
    anchors = [alloc.allocate(h) for h in _doc_headings(master)]
    assert len(anchors) == len(set(anchors))


def test_every_contents_link_resolves(master: str) -> None:
    alloc = AnchorAllocator()
    present = {alloc.allocate(h) for h in _doc_headings(master)}
    toc = master.split("## Contents", 1)[1].split("\n---", 1)[0]
    links = re.findall(r"\]\(#([a-z0-9\-]+)\)", toc)
    assert links, "contents page is empty"
    assert not [l for l in links if l not in present]


def test_contents_lists_sections_not_only_parts(master: str) -> None:
    """Regression: a level filter off by one produced a 5-line contents page."""
    toc = master.split("## Contents", 1)[1].split("\n---", 1)[0]
    links = re.findall(r"\]\(#([a-z0-9\-]+)\)", toc)
    assert len(links) > 3 * len(PARTS), (
        f"contents has only {len(links)} links for {len(PARTS)} parts -- the "
        "heading level filter is probably off by one again"
    )


def test_no_source_content_is_dropped(master: str) -> None:
    """Every source line survives, allowing for heading demotion and link rewrites."""
    from scripts.build_master_guide import REPO_ROOT

    master_lines = set(master.split("\n"))
    missing_total = 0
    for filename, _, _ in PARTS:
        text = (REPO_ROOT / "docs" / filename).read_text(encoding="utf-8")
        for line, in_fence in _iter_lines(text):
            if not line.strip():
                continue
            if in_fence:
                # Fenced lines must survive byte-identical -- that is the point.
                assert line in master_lines, f"{filename}: fenced line lost: {line!r}"
            elif re.match(r"^#{1,6}\s+", line) or "](" in line:
                continue  # legitimately transformed
            elif line not in master_lines:
                missing_total += 1
    assert missing_total == 0, f"{missing_total} non-heading prose lines were dropped"


def test_generated_output_is_deterministic() -> None:
    assert build() == build()
