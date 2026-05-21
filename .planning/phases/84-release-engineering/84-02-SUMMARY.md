---
phase: 84-release-engineering
plan: 02
subsystem: release-engineering
tags: [releng, changelog, towncrier, automation]
requires: [84-01]
provides: [towncrier-config, changelog-fragment-pipeline]
affects: [pyproject.toml, CHANGELOG.md, changelog.d/]
tech_stack:
  added:
    - "towncrier>=24.7.0 (dev dependency)"
  patterns:
    - "Per-PR news fragments under changelog.d/<id>.<kind>.md"
    - "Five section kinds: feature, bugfix, doc, removal, misc"
    - "Release-time prepend above <!-- towncrier release notes start --> marker"
key_files:
  created:
    - changelog.d/.gitkeep
    - changelog.d/README.md
    - changelog.d/v4.10.feature.md
  modified:
    - pyproject.toml
    - CHANGELOG.md
decisions:
  - "Use changelog.d/ (modern convention) over legacy news/ directory — matches Twisted, attrs, urllib3, pip, and current towncrier docs."
  - "Set package = \"quirk\" (Python import name) in [tool.towncrier], independent of PyPI distribution name (qu-i-r-k post-84-01). towncrier reads version from quirk.__version__, which closes the loop with the single-source-of-truth move done in plan 84-01."
  - "Keep-a-Changelog-compatible title_format `## [{version}] - {project_date}` so towncrier output matches the existing CHANGELOG.md style without manual reformatting."
  - "misc section uses showcontent=false — housekeeping commits surface only as a count, not noise in the release section."
metrics:
  duration_minutes: 8
  completed_date: 2026-05-21
  tasks_completed: 3
  files_changed: 5
  commits: 1
requirements_closed: [RELENG-04]
---

# Phase 84 Plan 02: Towncrier Changelog Automation Summary

Set up `towncrier` for per-PR CHANGELOG fragments under `changelog.d/`, eliminating
manual `CHANGELOG.md` editing at release time. Each PR now drops a one-line fragment;
`towncrier build` at release consumes fragments and prepends a Keep-a-Changelog-formatted
section above existing entries.

## What Was Built

### `[tool.towncrier]` config block (pyproject.toml)

- `package = "quirk"` — reads version from `quirk.__version__` (single source of truth
  pinned by plan 84-01).
- `directory = "changelog.d"`, `filename = "CHANGELOG.md"`.
- `title_format = "## [{version}] - {project_date}"` — matches Keep-a-Changelog heading
  style already in CHANGELOG.md.
- `start_string = "<!-- towncrier release notes start -->\n"` — towncrier prepends
  rendered sections above this marker, preserving the file's header.
- Five `[[tool.towncrier.type]]` entries:
  - `feature` → **Added** (showcontent=true)
  - `bugfix` → **Fixed** (showcontent=true)
  - `doc` → **Documentation** (showcontent=true)
  - `removal` → **Removed** (showcontent=true)
  - `misc` → **Misc** (showcontent=false, count-only)

### `[project.optional-dependencies] dev` group

New `dev` extras group containing `towncrier>=24.7.0`. Install via `pip install -e .[dev]`
to get the `towncrier` CLI for previewing and releasing.

### `changelog.d/` directory

- `.gitkeep` — keeps the empty dir committable between releases.
- `README.md` — documents filename convention (`<id>.<kind>.md`), all five kinds with
  rendering behavior, example fragments, and the `towncrier build --draft` / `build --yes`
  workflow.
- `v4.10.feature.md` — example fragment seeding the v4.10 release entry: "v4.10 Launch
  Readiness milestone: PyPI Trusted Publishers, Sigstore attestations, towncrier
  changelog automation, governance docs."

### `CHANGELOG.md` marker

Inserted `<!-- towncrier release notes start -->` immediately after the header / format
note and before the first version section (`## 4.4.0 - 2026-04-29`). Towncrier uses this
as the insertion point so the file's intro text is preserved across release builds.

## Verification

`towncrier build --draft --version 4.10.0` (with towncrier 25.8.0 in a clean venv) emits:

```
## [4.10.0] - 2026-05-21

### Added

- v4.10 Launch Readiness milestone: PyPI Trusted Publishers, Sigstore attestations,
  towncrier changelog automation, governance docs. (v4.10)
```

Plan automated checks (all pass):
- `grep -c '\[tool.towncrier\]' pyproject.toml` → 1
- `grep -c 'towncrier release notes start' CHANGELOG.md` → 1
- `test -f changelog.d/{.gitkeep,README.md,v4.10.feature.md}` → all present
- `towncrier build --draft --version 4.10.0 | grep -q 'v4.10 Launch Readiness'` → match

Draft output captured at `/tmp/towncrier-draft.txt` (not committed).

## Decisions Made

1. **`changelog.d/` over `news/`** — modern towncrier convention; matches Twisted,
   attrs, urllib3, pip. The PLAN explicitly noted this preference.
2. **`package = "quirk"` (import name), not `"qu-i-r-k"` (PyPI distribution name)** —
   towncrier reads `quirk.__version__`, which is the Python attribute on the
   installed package, not the wheel filename. Plan 84-01 decoupled these by renaming
   only the distribution name; `quirk` remains the Python package.
3. **Keep-a-Changelog `title_format`** — matches the existing CHANGELOG.md style so
   rendered sections look native, no post-processing required.
4. **`misc` section uses `showcontent = false`** — housekeeping fragments (dep bumps,
   CI tweaks) surface only as a count rather than polluting release notes with low-signal
   bullets.

## Deviations from Plan

### Worktree-baseline note (informational, not a deviation)

This plan ran inside a worktree branched from `19708ab` (v4.10 milestone init), **before**
plan 84-01's commit (`9288408`) landed. As a result, the worktree's `pyproject.toml` shows
`name = "quirk"` / `version = "4.4.0"` rather than the post-84-01 `qu-i-r-k` / `4.10.0`
state. This is the expected parallel-wave model — 84-01 and 84-02 changes are merged
together when the wave completes. The towncrier config (`package = "quirk"`) is correct
either way because it references the Python import name, not the distribution name.

### Phase directory creation (Rule 3 — blocking)

`.planning/phases/84-release-engineering/` did not exist in the worktree (created on main
in commit `9288408`). Created an empty directory in the worktree solely to hold this
SUMMARY file. When the worktree merges back, the directory will already exist on main; the
merge will simply add `84-02-SUMMARY.md` next to the existing PLAN files.

No other deviations.

## Known Stubs

None.

## Threat Flags

None — towncrier and the `changelog.d/` pipeline introduce no new network surface,
no auth path, no schema change. CHANGELOG.md remains a committed, public artifact.

## Self-Check: PASSED

- [x] `pyproject.toml` modified (1 `[tool.towncrier]` block, `towncrier>=24.7.0` in dev extras)
- [x] `CHANGELOG.md` modified (1 `<!-- towncrier release notes start -->` marker)
- [x] `changelog.d/.gitkeep` created
- [x] `changelog.d/README.md` created (documents kinds, naming, build commands)
- [x] `changelog.d/v4.10.feature.md` created (one-line example fragment)
- [x] Commit `fc07fff` exists on branch `worktree-agent-a2d1875d76e188004`
- [x] `towncrier build --draft --version 4.10.0` renders the example fragment under "Added"

## Commit

| Hash      | Subject                                                  |
| --------- | -------------------------------------------------------- |
| `fc07fff` | feat(84-02): towncrier changelog automation (RELENG-04) |

## Requirements Closed

- **RELENG-04** — Per-PR CHANGELOG fragments via towncrier; manual CHANGELOG edits no
  longer required at release time. Draft build verified.
