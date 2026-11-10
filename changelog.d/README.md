# changelog.d — retired; do not add fragments

**Release notes are written by hand, at release time, since 5.28.0.** Do not add files to
this directory. `tests/test_changelog_5280_section.py::test_fragments_consumed` requires it
to hold only this README (it lists the directory with `git ls-files`, so an untracked
fragment passes locally and fails in CI).

## Where a user-visible change goes instead

1. Record the item in `.planning/LEDGER.md` (or its todo), and say in the PR description
   what the release notes should tell users.
2. At release time, the release author writes the `## [X.Y.Z] - <date>` section of
   [`CHANGELOG.md`](../CHANGELOG.md) from those PR descriptions. `release.yml` turns that
   section into the GitHub release body and fails closed if it is missing.
3. `## [Unreleased]` stays empty between releases.

## Why

From 5.28.0 the notes have to explain score movement, known defects and upgrade steps in
prose (see the per-release guards `tests/test_changelog_528*_section.py`), which one-line
fragments could not carry. The `[tool.towncrier]` block in `pyproject.toml` and the
`<!-- towncrier release notes start -->` marker in `CHANGELOG.md` are leftovers; nothing
builds from them.
