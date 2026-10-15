---
type: todo
created: 2026-10-15
source: Phase 226 D-19 deferral
priority: low
area: README.md
status: pending
owner: v5.28
resolves_phase: 232
---

# README repo-relative links do not resolve on the PyPI page

**Owner phase:** v5.28

README's repo-relative links (LICENSE, docs/*.md, CHANGELOG.md, SECURITY.md) do not resolve on the PyPI
project page, because PyPI renders the README outside the repository. `[project.urls]` landed in 5.27.0,
which gives PyPI sidebar links, but the in-body links are still relative.

Fix options: rewrite the in-body links as absolute tag-pinned links
(`https://github.com/0xD1g5/QU.I.R.K/blob/v<version>/<path>`), gated the same way D-10 gates the tag-pinned
README images (derive the tag from pyproject, test that it resolves).

## Feasibility & Effort

- **Feasibility:** CONFIRMED. The README already uses tag-pinned absolute URLs for its images, so the
  mechanism and its gate exist; the links are plain Markdown.
- **Effort:** S.
- **Count the links:** `grep -nE '\]\((\./)?[A-Za-z][^:)]*\)' README.md | grep -v 'http'`
- **Unknowns:** none that need a spike.
