# Release Tag Hygiene guard counts a `workflow_dispatch` dry run as a release run for the tag

**Filed:** 2026-10-13 (Phase 224 gap closure C, docs/release-process.md audit)
**Priority:** P2 — the guard exists to catch a tag that never produced a release, and a dry run silences it
**Status:** open

## What happens

`scripts/release_tag_hygiene.py` lists runs with `gh run list --workflow release.yml --status success
--json displayTitle,headBranch` (`scripts/release_tag_hygiene.py:190-203`) and treats a run as backing a tag
when the tag equals the run's `headBranch` (`collect_backed_tags`, `scripts/release_tag_hygiene.py:56-80`).
The query never fetches the run's `event`. `release.yml` deliberately lets a `workflow_dispatch` run target a
tag ref and publish nothing (`.github/workflows/release.yml:97-101`), and for such a run `headBranch` is the tag
name. So `gh workflow run release.yml --ref vX.Y.Z` produces a successful run that backs `vX.Y.Z`, the guard
goes green, and nothing was published to PyPI and no Windows asset was attached.

Reproduced offline against the real functions:
`collect_backed_tags([{"headBranch": "v5.99.0", "displayTitle": "Release"}], [])` returns `{'v5.99.0'}` and
`evaluate_tags(["v5.99.0"], that_set, {})` flags nothing.

## Fix

Add `event` to the `--json` field list and count only runs whose `event` is `push`. Keep the existing
Release-object path (a GitHub Release object does back a tag). Add a unit test with a dispatch record that must
not back its tag. `docs/release-process.md` (Release Tag Hygiene Guard, remediation option 2) now tells
operators to push the tag again rather than dispatch against it, and says why.

## Feasibility & Effort

- Feasibility: CONFIRMED by calling the two functions directly with a dispatch-shaped record.
- Effort: S — one added JSON field, one filter, one test.
- Unknowns: whether any historical tag is backed only by a dispatch run (it would newly flag; review
  `gh run list --workflow release.yml --json event,headBranch` before merging).
- Spike needed: no.
