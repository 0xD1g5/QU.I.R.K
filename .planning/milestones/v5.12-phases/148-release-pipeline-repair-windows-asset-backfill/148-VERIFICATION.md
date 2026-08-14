---
phase: 148-release-pipeline-repair-windows-asset-backfill
verified: 2026-08-11T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 148: Release Pipeline Repair + Windows Asset Backfill Verification Report

**Phase Goal:** A release job that is broken can be caught before a tag is cut, and the specific
Windows-asset gap left by v5.11.0 is closed with a real, verified artifact.
**Verified:** 2026-08-11
**Status:** passed
**Re-verification:** No — initial verification

This phase's whole point was proving mechanisms work via real `workflow_dispatch` runs, not just
code inspection. Every claim below was independently re-checked against live GitHub state (fresh
`gh` calls made during this verification, not re-reading `148-04-EVIDENCE.md`) and against the
actual files on disk / on `origin/main`.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, cross-checked live)

| # | Truth (Success Criterion) | Status | Evidence |
|---|------|--------|----------|
| 1 | A manually-triggered dry-run (`workflow_dispatch`) exercises `windows-package` end-to-end without a git tag, reports pass/fail | ✓ VERIFIED | Live run `31524058796` (`gh run view 31524058796 --json conclusion,event,headBranch`) → `success`, `workflow_dispatch`, `main`. Independently re-fetched during this verification, matches EVIDENCE.md. `windows-package` job conclusion `success`; `publish` job conclusion `skipped`. |
| 2 | The `1a6effc` signing self-test repair is proven passing by an actual green CI run, not code inspection | ✓ VERIFIED | Step `CI self-test — ephemeral cert signing round-trip` inside run `31524058796` → `success` (re-verified live via `gh run view ... --json jobs`). Log line `SELF_TEST_SIGNING: OK` recorded in EVIDENCE.md (log re-fetch not re-run here since GH log retention makes exact byte match unnecessary given the step conclusion is independently confirmed `success`). |
| 3 | A malformed (`v5.9`) or unpushed (`v5.10.0`) tag is detectably different from a successful release run via a documented check/guard | ✓ VERIFIED | Live run `31524420671` (`release-tag-hygiene.yml`) → `success`, `workflow_dispatch`, event confirmed live. `.github/tag-hygiene-baseline.txt` on disk contains explicit `v5.9`, `v5.10.0`, `v5.11.0` entries with incident-specific reasons (re-grepped directly, not copied from EVIDENCE.md). `scripts/release_tag_hygiene.py`'s `LOOSE_RELEASE_TAG_RE = ^v[0-9]` deliberately catches the `v5.9` two-component case that `release.yml`'s strict `v*.*.*` misses — confirmed by reading the interface contract and the 51-test local suite (all passing). |
| 4 | The v5.11.0 Windows-asset gap is resolved per D-148-RELEASE04 — operator can tell without guessing whether a Windows artifact exists | ✓ VERIFIED | Live `gh release view v5.11.0 --json tagName,assets,isDraft,isPrerelease` (freshly run, not read from EVIDENCE.md) → `tagName=v5.11.0`, `assets=0`, `isDraft=false`, `isPrerelease=false`. `gh release list` includes `v5.11.0`, excludes `v5.9`/`v5.10.0` (no fabricated Release objects). Release body (live-fetched) contains `PyPI-only`, `1a6effc`, `v5.12.0`, and a link to `docs/release-notes/5.11.0.md`. |
| 5 (PLAN-level, 148-04) | Both live runs (dry-run + tag-hygiene) and the Release object all match the mechanism built in 148-01/02/03 — no drift between "what was built" and "what was proven" | ✓ VERIFIED | `.github/workflows/release.yml` guard literals independently re-parsed with `yaml.safe_load` during this verification (not reused from SUMMARY) — `publish` job guard, `Attach zip to GitHub Release` step guard, and `Upload dry-run zip artifact` complement guard all present and correctly polarized. Step ordering (`Assemble → Upload dry-run → Attach`) confirmed via fresh YAML parse. `origin/main` HEAD (`60955b8...`) matches the SHA the live runs actually executed against; local `HEAD` is 3 commits ahead but those are `.planning/` docs-only commits (ROADMAP/STATE/148-04-EVIDENCE/148-04-SUMMARY) — no functional file drift. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/release.yml` | `workflow_dispatch` trigger + byte-identical event+ref guards + dry-run upload | ✓ VERIFIED | Live-parsed YAML confirms all four D-05/D-06/D-07 edits present and correctly ordered. |
| `tests/test_release_workflow_dryrun_guards.py` | Static guard test, ≥60 lines | ✓ VERIFIED | 219 lines, part of the 51-test suite that passes clean (re-run during this verification). |
| `docs/release-process.md` | Pre-tag dry-run runbook step + Tag Hygiene Guard section | ✓ VERIFIED | `## Release Runbook`, `## Release Tag Hygiene Guard` headings present; content re-grepped. |
| `scripts/release_tag_hygiene.py` | Pure decision function + CLI, ≥80 lines | ✓ VERIFIED | 237 lines; `python -m compileall` exits 0; exports match interface contract. |
| `tests/test_release_tag_hygiene.py` | Unit tests, ≥60 lines | ✓ VERIFIED | 238 lines, part of passing suite. |
| `.github/workflows/release-tag-hygiene.yml` | Monday 09:00 UTC cron + manual dispatch | ✓ VERIFIED | 50 lines; live-dispatched and green (run `31524420671`). |
| `.github/tag-hygiene-baseline.txt` | Historical exemptions, contains `v5.9` | ✓ VERIFIED | 32 non-comment entries == `git tag --list` count (re-verified). Contains `v5.9`, `v5.10.0`, `v5.11.0` with incident-specific reasons. |
| `docs/release-notes/5.11.0.md` | Full disposition, `PyPI-only`, ≥40 lines | ✓ VERIFIED | 77 lines; contains all required disposition facts (re-grepped). |
| `docs/release-notes/5.11.0-github-release-body.md` | Ready-to-publish Release body, contains `1a6effc` | ✓ VERIFIED | 17 lines; content matches what was actually published live (byte-for-byte comparable to `gh release view v5.11.0 --json body`). |
| `tests/test_release_notes_5_11_0.py` | Static drift-lock, ≥40 lines | ✓ VERIFIED | 144 lines, part of passing suite. |
| `.planning/phases/.../148-04-EVIDENCE.md` | Run IDs/URLs/conclusions, ≥40 lines | ✓ VERIFIED | 197 lines. Cross-checked against independently-run `gh` queries during this verification — every conclusion, job name, and step name matched exactly. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `release.yml` | `publish` job | job-level event+ref guard | ✓ WIRED | Live-parsed; also live-proven (`publish` conclusion `skipped` on real dispatch). |
| `release.yml` | `Attach zip to GitHub Release` step | step-level event+ref guard | ✓ WIRED | Live-parsed; also live-proven (step conclusion `skipped`). |
| `test_release_workflow_dryrun_guards.py` | `release.yml` | `yaml.safe_load` | ✓ WIRED | 51/51 tests pass locally. |
| `release-tag-hygiene.yml` | `scripts/release_tag_hygiene.py` | `run: python scripts/...` | ✓ WIRED | Live-dispatched run executed the script and produced the expected EXEMPT/OK/FLAGGED summary content. |
| `release_tag_hygiene.py` | `$GITHUB_STEP_SUMMARY` | summary markdown write | ✓ WIRED | Confirmed via `grep -c GITHUB_STEP_SUMMARY` ≥1 and the live run producing summary output. |
| `5.11.0-github-release-body.md` | `5.11.0.md` | absolute GitHub blob URL | ✓ WIRED | Live `gh release view v5.11.0 --json body` confirms the link is present in the *published* body, not just the source file. |

### Behavioral Spot-Checks / Live Probe Execution

This phase's entire verification model is "live GitHub run, not code inspection" — the required
"probes" are the two live `workflow_dispatch` runs and the `gh release view` check. All three were
independently re-executed during this verification session (not merely re-read from
`148-04-EVIDENCE.md`):

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Dry-run overall conclusion | `gh run view 31524058796 --json conclusion,event,headBranch` | `success`, `workflow_dispatch`, `main` | ✓ PASS |
| Dry-run job conclusions | `gh run view 31524058796 --json jobs -q '.jobs[]...'` | build=success, windows-package=success, publish=skipped | ✓ PASS |
| Dry-run step conclusions | `gh run view 31524058796 --json jobs -q '...steps[]...'` | self-test=success, upload-dry-run=success, attach-to-release=skipped | ✓ PASS |
| Dry-run artifact | `gh api .../actions/runs/31524058796/artifacts` | `quirk-windows-dry-run` 57,330,823 bytes | ✓ PASS |
| Tag-hygiene run | `gh run view 31524420671 --json conclusion,event,workflowName` | `success`, `workflow_dispatch`, `Release Tag Hygiene` | ✓ PASS |
| v5.11.0 Release state | `gh release view v5.11.0 --json tagName,assets,isDraft,isPrerelease` | `v5.11.0`, 0 assets, false, false | ✓ PASS |
| v5.11.0 Release list membership | `gh release list --json tagName` | includes `v5.11.0`, excludes `v5.9`/`v5.10.0` | ✓ PASS |
| Local guard suite | `pytest tests/test_release_workflow_dryrun_guards.py tests/test_release_tag_hygiene.py tests/test_release_notes_5_11_0.py -q` | 51 passed | ✓ PASS |
| YAML guard literals | `python -c "import yaml..."` (plan's own verify command) | `OK` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RELEASE-02 | 148-01, 148-04 | Broken release job caught before tag is cut (dry-run) | ✓ SATISFIED | Live green `workflow_dispatch` run + test-enforced guards. REQUIREMENTS.md row `Phase 148 — Complete`. |
| RELEASE-03 | 148-02, 148-04 | Malformed/unpushed tag cannot silently skip signal | ✓ SATISFIED | Live green tag-hygiene run naming `v5.9`/`v5.10.0` as EXEMPT with reasons; scheduled Monday-cron + on-demand dispatch. REQUIREMENTS.md row `Phase 148 — Complete`. |
| RELEASE-04 | 148-03, 148-04 | v5.11.0 gap retroactively completed or dispositioned | ✓ SATISFIED | Live bare Release, zero assets, disposition body live-confirmed. REQUIREMENTS.md row `Phase 148 — Complete`. |

No orphaned requirements: REQUIREMENTS.md maps exactly RELEASE-02/03/04 to Phase 148, and all three
appear in plan frontmatter (`148-01`, `148-02`, `148-03`, and all three again in `148-04`).
RELEASE-01 is explicitly mapped to Phase 153 (out of scope here, correctly deferred — depends on
this phase's dry-run mechanism per CONTEXT.md canonical refs).

### Anti-Patterns Found

None. Scanned all phase-modified files (`release.yml`, `release-tag-hygiene.yml`,
`release_tag_hygiene.py`, `docs/release-notes/5.11.0.md`, `5.11.0-github-release-body.md`,
`docs/release-process.md`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|not yet implemented|coming soon`
— zero matches.

### Context Decisions (D-01..D-12) Honored

- D-01/D-02/D-03/D-04 (Windows asset disposition, Option B): confirmed live — bare Release, zero
  assets, `--latest=false` used (v5.8.0 still shows as latest, matches live `gh release list`
  ordering convention), disposition prose present in both the notes file and the published body.
- D-05/D-06/D-07 (dry-run mechanism): confirmed via live-parsed YAML and a live dispatch proving
  the event-name conjunct actually gates the `publish` job and the `Attach zip` step under a real
  run (not just a static assertion).
- D-06 correction (event-name conjunct mandatory, not ref-shape-only): the static test
  `test_no_guard_is_ref_shape_only` is part of the passing 51-test suite; this specific edge case
  (dispatch against a tag ref) was deliberately NOT live-tested per the plan's own interface note
  ("do not just try it to be sure") — an intentional, documented scope boundary, not a gap.
- D-09..D-12 (tag hygiene guard): confirmed live — scheduled cron present, no `push`/`pull_request`
  trigger, baseline seeded with all 32 pre-existing tags, `v5.9`/`v5.10.0`/`v5.11.0` carry specific
  reasons.

### Human Verification Required

None. This phase's entire evidentiary model is live-run verification, and every required live
check was independently re-executed during this verification session with results matching
`148-04-EVIDENCE.md` exactly. No visual, UX, or subjective judgment items remain.

### Process/Documentation Compliance Note (non-blocking)

CLAUDE.md's "Mandatory Phase Completion Steps" (which this project's own instructions require at
the end of every `/gsd:execute-phase` run) call for an Obsidian phase note under
`20_Dev-Work/QUIRK/Phases/Phase-148-*.md` and a `docs/UAT-SERIES.md` entry for this phase. Neither
was found:

- `ls "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/"` shows no `Phase-148-*` note.
- `grep -n "Phase 148" docs/UAT-SERIES.md` returns no matches.

This does not affect the phase's technical goal achievement (RELEASE-02/03/04 are all live-proven),
so it is called out here as a WARNING rather than a BLOCKER — it is a process-completeness gap the
project's own CLAUDE.md treats as mandatory, and should be closed out (either now or explicitly
deferred) before the milestone considers this phase fully wrapped.

### Gaps Summary

No gaps against the phase's must-haves, roadmap Success Criteria, or requirement IDs — all were
independently re-verified live during this session, not merely re-read from SUMMARY/EVIDENCE files.
The only open item is the non-blocking CLAUDE.md process-compliance note above (missing Obsidian
phase note + UAT-SERIES.md entry for Phase 148).

---

_Verified: 2026-08-11_
_Verifier: Claude (gsd-verifier)_
