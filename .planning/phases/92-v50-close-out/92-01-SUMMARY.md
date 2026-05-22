---
phase: 92-v50-close-out
plan: "01"
subsystem: release-engineering
tags: [version-bump, changelog, release-notes, towncrier, pqc, releng]
dependency_graph:
  requires: [87-01, 87-02, 88-01, 88-02, 89-01, 89-03, 90-01, 90-03, 91-02]
  provides: [v5.0.0-version-bump, v5.0.0-changelog, v5.0.0-release-notes, v5.0.0-tag]
  affects:
    - pyproject.toml
    - CHANGELOG.md
    - docs/release-notes/5.0.0.md
tech_stack:
  added: [towncrier>=25.8.0 (dev dep, invoked from .venv)]
  patterns: [towncrier-fragment-pipeline, single-source-version-pyproject]
key_files:
  created:
    - docs/release-notes/5.0.0.md
  modified:
    - pyproject.toml
    - CHANGELOG.md
decisions:
  - "D-00 honored: pyproject.toml [project.version] is sole SoT; quirk/__init__.py unchanged"
  - "D-01 honored: towncrier pipeline used; fragments created, then towncrier build --version 5.0.0 --yes built CHANGELOG section; no hand-editing"
  - "D-02 honored: local annotated v5.0.0 tag created; not pushed to origin"
  - "Version resolution path: importlib.metadata (installed via .venv editable reinstall); tomllib fallback untouched"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-22"
  tasks_completed: 2
  files_changed: 3
---

# Phase 92 Plan 01: v5.0.0 Version Bump + CHANGELOG + Release Notes Summary

## One-liner

pyproject.toml bumped to 5.0.0 (all three surfaces agree), towncrier built the ## [5.0.0] CHANGELOG section from five phase fragments (87-91), and docs/release-notes/5.0.0.md written with the OQS-nginx PQC-hybrid scoring-ceiling headline.

## What Was Built

### Task 1: Version bump to 5.0.0 (commit d6c43f0)

Edited `pyproject.toml` `[project] version` from `4.10.1` to `5.0.0` (one-line change, sole SoT).

Verification:

- `grep 'version = "5.0.0"' pyproject.toml` — PASS
- `.venv/bin/pip install -e . --no-deps` refreshed importlib.metadata
- `.venv/bin/python -c "import quirk; print(quirk.__version__)"` → `5.0.0`
- `.venv/bin/quirk --version` → `QU.I.R.K. v5.0.0`

`quirk/__init__.py` unchanged — `__version__` still derives via `importlib.metadata.version("quirk-scanner")` with the tomllib fallback for bare checkouts.

### Task 2: Towncrier fragments, CHANGELOG build, release notes (commit add338c)

**Fragments created in `changelog.d/`** (sourced from phase 87-91 SUMMARYs):

| Fragment | Kind | Phase | Content summary |
|----------|------|-------|-----------------|
| v5.0-87.misc.md | misc | 87 | Node 20→24 CI bump + lxml/XXE xml_safe chokepoint (defusedxml removal) |
| v5.0-88.bugfix.md | bugfix | 88 | Subscore decomposition on all report surfaces + CBOM zero-algo coverage notes |
| v5.0-89.feature.md | feature | 89 | Four weak-TLS lab profiles: postgres-tls, redis-tls, kafka-tls, grpc-tls |
| v5.0-90.feature.md | feature | 90 | OQS-nginx PQC-hybrid profile (X25519MLKEM768) + agility_pqc_hybrid_bonus=8.0 |
| v5.0-91.misc.md | misc | 91 | Dead-code removal (writer.py), Phase 77 D-15 conflict resolution, vulture catalogue |

**`towncrier build --version 5.0.0 --yes`** ran cleanly:
- Prepended `## [5.0.0] - 2026-05-22` section above `<!-- towncrier release notes start -->` in CHANGELOG.md
- Section contains: Added (2 bullets — phases 89 and 90), Fixed (1 bullet — phase 88), Misc (v5.0-87, v5.0-91)
- All five fragments deleted from `changelog.d/` by towncrier (disk deletion succeeded; `git rm` step emitted a benign "No pathspec" error because fragments were not previously tracked)

**`docs/release-notes/5.0.0.md`** written:
- Headline: OQS-nginx PQC-hybrid profile (X25519MLKEM768 hybrid KEM, ML-DSA-65 cert, port 39444, agility_pqc_hybrid_bonus=8.0)
- Phase-by-phase coverage: 90 (PQC-hybrid), 88 (scoring transparency), 89 (four lab profiles), 87 (dependency hygiene), 91 (code cleanup)
- Framed as stabilization + tech-debt-sweep release (no new capability beyond the PQC anchor)
- No secrets, internal absolute paths, or vault filesystem paths (T-92-01 satisfied)

**`python -m compileall -q quirk`** — clean.

**Local annotated tag `v5.0.0` created** (D-02; not pushed to origin).

## Deviations from Plan

### Minor Deviation: towncrier git rm benign error

- **Found during:** Task 2 — `towncrier build --version 5.0.0 --yes` stderr showed `fatal: No pathspec was given. Which files should I remove?`
- **Cause:** The five changelog.d/ fragments were created as untracked new files, never committed separately. Towncrier's `git rm` step only works when fragments are already tracked by git; for new untracked files it deletes them from disk (succeeded) but the `git rm` fails silently.
- **Impact:** Zero — the files were deleted from disk correctly. CHANGELOG.md was staged by towncrier. The untracked fragments do not appear in `git status`.
- **Action:** None required. Not a bug in QUIRK code.

## Known Stubs

None — pyproject.toml is at 5.0.0, all three surfaces agree, CHANGELOG.md has the towncrier-built section, and release notes exist.

## Threat Flags

None — release text sourced exclusively from phase SUMMARY files and public documentation. No secrets, internal paths, or vault filesystem paths appear in CHANGELOG.md or docs/release-notes/5.0.0.md (T-92-01 verified by grep before commit).

## Self-Check: PASSED

- pyproject.toml contains `version = "5.0.0"`: FOUND
- CHANGELOG.md contains `## [5.0.0]`: FOUND
- docs/release-notes/5.0.0.md exists with "pqc" content: FOUND
- changelog.d/ has only README.md (fragments consumed): CONFIRMED
- Commit d6c43f0 (Task 1): FOUND
- Commit add338c (Task 2): FOUND
- Local tag v5.0.0: FOUND
- `python -m compileall -q quirk` clean: CONFIRMED
