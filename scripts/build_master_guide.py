#!/usr/bin/env python3
"""Assemble the five operator guides into one master document.

WHY A GENERATOR AND NOT A HAND-MERGED FILE
------------------------------------------
The five source guides stay canonical: they are what CLAUDE.md's per-phase
documentation checklist maps change types onto, and what the Obsidian sync
table points at. A hand-merged master would be stale the moment anyone edited
a source, leaving two contradictory descriptions of the same behaviour -- the
exact drift class the 2026-09-16 reconciliation existed to remove. Deriving it
means the master cannot disagree with its sources, only lag them, and the lag
is one command wide.

    .venv/bin/python -m scripts.build_master_guide > docs/quirk-master-guide.md

WHAT IT HAS TO GET RIGHT
------------------------
Code fences. `grep -c '^# '` reports 33 top-level headings in configuration.md
and 8 in getting-started.md; the real counts are 1 each. The rest are shell
comments inside ```bash blocks (`# Positional token ...`). Any transform that
rewrites headings without tracking fences corrupts every code example it
touches, silently, in a 6,000-line document nobody will re-read line by line.
`_iter_lines` is therefore the only place lines are classified, and it is the
one piece worth testing.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# Reading order, not alphabetical: a newcomer's path through the product.
# (source filename, part title, one-line purpose)
PARTS: List[Tuple[str, str, str]] = [
    ("getting-started.md", "Getting Started",
     "First scan, first report, and what the output means."),
    ("installation.md", "Installation",
     "Platform-by-platform install, optional extras, and PDF-export prerequisites."),
    ("configuration.md", "Configuration",
     "Every config key, connector, integration and environment variable."),
    ("operators-guide.md", "Operator's Guide",
     "Running scans in anger: per-scanner reference, troubleshooting, sensors, hardware."),
    ("admin-guide.md", "Administration",
     "Console deployment, sensor enrolment, token lifecycle and hardening."),
]

FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# Links into a sibling guide: (installation.md) or (installation.md#anchor)
SIBLING_LINK_RE = re.compile(r"\]\((?:\./)?([a-z0-9-]+\.md)(#[a-z0-9-]*)?\)")


@dataclass
class Part:
    slug: str
    title: str
    purpose: str
    body: str
    headings: List[Tuple[int, str, str]]


def _iter_lines(text: str) -> Iterator[Tuple[str, bool]]:
    """Yield (line, in_code_fence).

    Tracks ``` and ~~~ fences including longer runs and language suffixes. A
    fence closes only on the same marker character, so a ~~~ block containing a
    ``` line stays open -- which is how nested examples are written.
    """
    fence_char: str | None = None
    fence_len = 0
    for line in text.split("\n"):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            char, length = marker[0], len(marker)
            if fence_char is None:
                fence_char, fence_len = char, length
                yield line, True
                continue
            if char == fence_char and length >= fence_len:
                fence_char, fence_len = None, 0
                yield line, True
                continue
        yield line, fence_char is not None


def base_anchor(title: str) -> str:
    """GitHub-compatible anchor slug, before de-duplication."""
    s = title.lower()
    s = re.sub(r"`|\*|_|\[|\]|\(|\)|\.|,|:|;|/|\\|\+|&|'|\"", "", s)
    s = re.sub(r"[^a-z0-9\- ]", "", s)
    return re.sub(r"\s+", "-", s.strip())


class AnchorAllocator:
    """Reproduce GitHub's positional de-duplication of repeated headings.

    Merging five guides collides 9 anchors across 25 of 302 headings -- seven
    headings slug to `#prerequisites` alone. GitHub resolves this by appending
    -1, -2 ... in document order, so a table of contents built from bare slugs
    sends six of those seven links to the first section. Allocating anchors in
    the same order GitHub renders them keeps the contents honest.
    """

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def allocate(self, title: str) -> str:
        base = base_anchor(title)
        n = self._seen.get(base, 0)
        self._seen[base] = n + 1
        return base if n == 0 else f"{base}-{n}"


def anchor_for(title: str) -> str:
    """First-occurrence anchor. Only safe for titles known to be unique."""
    return base_anchor(title)


def load_part(filename: str, title: str, purpose: str, anchors: AnchorAllocator) -> Part:
    src = REPO_ROOT / "docs" / filename
    text = src.read_text(encoding="utf-8")
    slug = anchors.allocate(title)

    out: List[str] = []
    headings: List[Tuple[int, str, str]] = []
    seen_h1 = False

    for line, in_fence in _iter_lines(text):
        if in_fence:
            out.append(line)
            continue
        m = HEADING_RE.match(line)
        if not m:
            # Rewrite sibling-guide links to in-document anchors.
            line = SIBLING_LINK_RE.sub(_rewrite_link, line)
            out.append(line)
            continue

        level, htext = len(m.group(1)), m.group(2).rstrip()
        if level == 1 and not seen_h1:
            # The source's own title becomes the part heading; drop it here.
            seen_h1 = True
            continue
        new_level = min(level + 1, 6)
        out.append("#" * new_level + " " + htext)
        anchor = anchors.allocate(htext)
        if new_level <= 3:
            headings.append((new_level, htext, anchor))

    body = "\n".join(out).strip("\n")
    return Part(slug=slug, title=title, purpose=purpose, body=body, headings=headings)


_FILE_TO_TITLE = {f: t for f, t, _ in PARTS}


def _rewrite_link(m: re.Match) -> str:
    filename, frag = m.group(1), m.group(2)
    if filename in _FILE_TO_TITLE:
        # Same-document now: keep the fragment, or point at the part.
        return "](" + (frag or "#" + anchor_for(_FILE_TO_TITLE[filename])) + ")"
    # A guide outside this master (chaos-lab.md, report-interpretation.md...).
    # Leave it relative; the master lives in the same docs/ directory.
    return m.group(0)


def build() -> str:
    anchors = AnchorAllocator()
    parts = [load_part(f, t, p, anchors) for f, t, p in PARTS]
    total = sum(p.body.count("\n") + 1 for p in parts)

    L: List[str] = []
    L.append("# QU.I.R.K. — Complete Guide")
    L.append("")
    L.append("> **Generated file — do not edit.** This document is assembled from the five")
    L.append("> operator guides listed below, which remain the canonical sources. Edit those,")
    L.append("> then regenerate:")
    L.append(">")
    L.append("> ```bash")
    L.append("> .venv/bin/python -m scripts.build_master_guide > docs/quirk-master-guide.md")
    L.append("> ```")
    L.append(">")
    L.append("> Editing this file directly loses the change on the next regeneration and puts")
    L.append("> two contradictory descriptions of the same behaviour in the repository.")
    L.append("")
    L.append(f"Five guides, {total:,} lines, in reading order.")
    L.append("")
    L.append("| Part | Source | Covers |")
    L.append("|------|--------|--------|")
    for p, (f, _, _) in zip(parts, PARTS):
        L.append(f"| [{p.title}](#{p.slug}) | `docs/{f}` | {p.purpose} |")
    L.append("")
    L.append("Guides deliberately **not** merged here, because they are reference rather than")
    L.append("operation: [`chaos-lab.md`](chaos-lab.md), [`report-interpretation.md`](report-interpretation.md),")
    L.append("[`architecture.md`](architecture.md), [`error-codes.md`](error-codes.md) (generated),")
    L.append("and the connector guides under [`connectors/`](connectors/).")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Contents")
    L.append("")
    for p in parts:
        L.append(f"- **[{p.title}](#{p.slug})**")
        # Source `##` headings become level 3 after demotion -- that is the
        # section level a reader navigates by. Filtering on level 2 here emitted
        # a five-line contents page for a 6,400-line document.
        for level, htext, anchor in p.headings:
            if level == 3:
                L.append(f"  - [{htext}](#{anchor})")
    L.append("")

    for p in parts:
        L.append("")
        L.append("---")
        L.append("")
        L.append(f"# {p.title}")
        L.append("")
        L.append(f"*{p.purpose}*")
        L.append("")
        L.append(p.body)
        L.append("")

    return "\n".join(L).rstrip("\n") + "\n"


if __name__ == "__main__":
    sys.stdout.write(build())
