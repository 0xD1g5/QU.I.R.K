# 999.109 — GitHub release bodies are static Windows-sensor boilerplate for every tag

**Filed:** 2026-09-11 (from `.planning/debug/github-release-notes-and-ci-failures.md`, investigated same day)
**Priority:** P2 — every published release describes "deploying Windows sensors" instead of what
shipped. Public-facing credibility issue on the release history page; README/landing content is fine.

## STATUS: workflow fix IMPLEMENTED 2026-09-13, branch `fix-999.109-release-body`

**Scope was 7 releases, not 3.** The line below originally read "confirmed byte-identical on
v5.18.0, v5.19.0, v5.21.0" — that was the sample checked, not the set. Re-enumerated 2026-09-13 by
querying every release rather than trusting the filed figure: the boilerplate is on **v5.7.0,
v5.8.0, v5.12.0, v5.15.0, v5.18.0, v5.19.0 and v5.21.0**. `v5.11.0` already carries a proper custom
body and must be left alone. All 7 have matching `## [x.y.z]` CHANGELOG sections.

Implemented (commits `7b9eb4cc`, `bd0cb3ba`): a "Compose release notes from CHANGELOG" step writes
`release-notes.md`, and the attach step consumes it via `body_path`. Two things the fix shape below
did not anticipate:

- **The job runs on `windows-latest`**, so the extraction is PowerShell, not awk. A PowerShell
  here-string cannot be used inside YAML's `run: |` block scalar — it forces content to column 1,
  which escaped the scalar and made a bare `---` line parse as a YAML document separator.
- **The step is deliberately NOT gated on the tag push**, contradicting "testable only on the next
  real tag push" below. Composing a markdown file has no side effects, so it runs on
  `workflow_dispatch` dry-runs too and uploads `release-notes.md` as an artifact. That earned itself
  immediately: the first dry-run (run 34783338643) exposed a stray bare-backtick line in the install
  snippet, fixed and re-verified green (run 34783597094). Waiting for a real tag would have shipped
  it.

**Still outstanding:** backfilling the 7 existing public release bodies via `gh release edit`
(operator action — rewrites public pages; back up the current bodies first, they are not
recoverable from GitHub once overwritten).

## Root cause (confirmed)

`.github/workflows/release.yml:303-348` — the "Attach zip to GitHub Release" step
(`softprops/action-gh-release`) hardcodes a static `body:` block (Windows Sensor Asset /
UNSIGNED BINARY NOTICE) for every tag push. It never reads `CHANGELOG.md` and never
interpolates the version; unparameterized since ~Phase 118.

## Fix shape

Add a step before "Attach zip to GitHub Release" that extracts the matching `## [x.y.z]` section
from `CHANGELOG.md` (keyed off `steps.version.outputs.version`) and **prepends** it to the
existing static Windows-sensor notice (the notice is still accurate and must stay — the binary
really is unsigned). Optionally backfill the existing wrong release bodies via `gh release edit`
as a one-time operator action.

## Feasibility & Effort

- **Feasibility: CONFIRMED** — root cause is a literal hardcoded YAML block at a known line
  range; `softprops/action-gh-release` supports `body_path`/`body` inputs, and `CHANGELOG.md`
  already carries correct per-version sections (verified for v5.21).
- **Effort: S** — one workflow step (awk/sed extraction to a file + `body_path`), testable only
  on the next real tag push (release.yml fires on `v[0-9]*` — NO test tags; per project
  convention milestone closes do not tag, so this waits for the next release phase).
- **Unknowns:** exact `CHANGELOG.md` heading format stability across versions (verify the
  extraction regex against all existing sections); whether the backfill of old releases is
  wanted (operator decision).
- **Spike needed: no.**

## Hazard notes

- Do NOT push any tag to test this — `release.yml` triggers on `v[0-9]*` and publishes to PyPI
  (Phase 187 lesson). Validation is by workflow-syntax check + dry extraction of the CHANGELOG
  section locally; live proof lands with the next genuine release (e.g. v5.23.0's release phase).
