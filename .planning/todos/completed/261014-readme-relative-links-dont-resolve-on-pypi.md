---
type: todo
created: 2026-10-15
source: Phase 226 D-19 deferral
priority: low
area: README.md
status: completed
completed: 2026-10-27
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

## Resolution (Phase 232, 2026-10-27)

- **Fix.** Every repo-relative README link, **25** of them (23 files and 2 directories, `examples/cbom/` and
  `docs/connectors/`), now points at `https://github.com/0xD1g5/QU.I.R.K/blob/v5.27.0/<path>`, or `/tree/` for
  the two directories, with anchors kept (D-11). The count is 25, not the grep above: that grep misses the
  three badge links on lines 9-11, which share a line with an `http` URL. Commit `5486d5ba` (POLISH-04).
- **Gate.** New `tests/test_readme_links_pinned.py`, offline, 14 nodes. It derives the pin from
  `pyproject_version()` (the 3.10-safe helper from 232-02), fails on any relative link or any repo link not
  pinned to `v<version>`, checks blob/tree kind and anchors against git objects at HEAD, and cross-checks its
  tokenizer against markdown-it-py (38 = 38 URLs). Five mutations proven red (232-04 SUMMARY). 14 passed on
  2026-10-27; UAT-232-07.
- **Ledger.** The rewrite broke **26** doc-claim ledger rows, exactly the research list; all 26 were
  re-anchored in the same commit, and `tests/test_doc_claim_ledger_gate.py` is green.
- **Live evidence.** `curl -sI` on the 16 unique pinned GitHub URLs returned HTTP 200 for all 16. No PyPI page
  was checked.
- **Hand-off to Phase 235 (D-13).** "Every README link resolves on the PyPI project page" can only be observed
  after the `v5.28.0` tag and upload. It belongs to Phase 235 LAUNCH-03 (fresh-install and README smoke), not a
  232 gap; UAT-232-08 is SKIP DEFERRED to the offline pin gate for that reason.
- **Version-bump coupling.** Because the pin derives from pyproject, Phase 235's version bump turns the gate
  red until these 25 link pins move together with the 4 README image pins (proven by 232-04's M4 mutation).
