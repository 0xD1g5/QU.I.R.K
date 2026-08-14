---
phase: 153-release-tag-cut
verified: 2026-08-14T11:50:00Z
status: human_needed
score: 12/13 must-haves verified
overrides_applied: 0
gaps: []
human_verification:
  - test: "Confirm the docs-only commits made after the tag cut (879f755, 035c24d, f8b282e) are pushed to origin/main before Phase 153 is closed"
    expected: "`git rev-list --left-right --count origin/main...HEAD` returns `0 0` (in sync)"
    why_human: "Not a code-correctness question — a deliberate operator decision on whether to push now or as part of the phase-close sequence. Currently local `main` is 3 commits ahead of `origin/main` (the Series 153 UAT entry commit, its --no-ff merge, and the WR-01 review-fix commit). This does not affect the already-proven RELEASE-01 tag/CI/asset evidence (all of that lived on `83ac92d`, which IS on origin and already tag-pushed), but per this project's norms (public repo, CLAUDE.md's push-to-remote-facing conventions) these should reach origin before/at phase close."
---

# Phase 153: Release Tag Cut Verification Report

**Phase Goal:** Cutting the real v5.12.0 release tag proves every repaired signal end-to-end on an
actual immutable tag — the only proof RELEASE-01 admits — and the milestone's own close-out is the
first phase gated by the new ARTIFACT enforcement.
**Verified:** 2026-08-14T11:50:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

All load-bearing technical claims were independently re-derived against live GitHub/PyPI state
(not read from SUMMARY.md prose). One non-blocking operational item (unpushed docs commits) and
one already-approved human-gated checkpoint are flagged for explicit human sign-off; nothing was
found FAILED.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `origin/main` was in sync with local `main` before the tag, and real CI (Python CI, Dashboard Quality, Python Staleness Gate) was green on that exact SHA | ✓ VERIFIED | `gh run list --branch main --limit 3 --json headSha,name,conclusion` independently re-run: all 3 workflows `conclusion: "success"` on `headSha: 83ac92d993b018e67b1f6a568251bedc9cc14188` — the same SHA later tagged |
| 2 | A `workflow_dispatch` dry-run of `release.yml` ran the windows-package job with a passing signing self-test and zero publish/attach side effects | ✓ VERIFIED | `gh run view 31768252469 --json event,conclusion,jobs`: `event: workflow_dispatch`, `conclusion: success`; jobs show `Build wheel + sdist` success, `Build Windows zip + attach GitHub Release asset` success, `Publish to PyPI` **skipped** — confirms the event-gate held live |
| 3 | `pyproject.toml`'s version is the sole canonical `5.12.0` edit, and all 6 derived-surface tests pass | ✓ VERIFIED | `grep '^version' pyproject.toml` → `version = "5.12.0"`; `.venv/bin/pytest tests/test_version.py -q` → `6 passed, 1 deselected` |
| 4 | Every manual version literal (README heading, UAT-SERIES header + UAT-1-02) reads 5.12.0, not 5.11.0 | ✓ VERIFIED | `README.md:7` → `# QU.I.R.K. — v5.12.0`; `docs/UAT-SERIES.md:3` → `**Version:** 5.12.0`; UAT-1-02 Pass Criteria → `QU.I.R.K. v5.12.0` |
| 5 | `docs/release-notes/5.12.0.md` exists, documents the milestone, and explicitly states the v5.11.0 Windows-asset gap is now closed | ✓ VERIFIED | File read directly — H1/Released/Milestone/What's New (6 phase bullets)/Known Issues ("Windows — Asset Gap Closed", cites RELEASE-01)/Upgrade Guidance/See Also, matching the 5.11.0.md structure |
| 6 | A human explicitly confirmed the irreversible tag push before it happened; no autonomous auto-chain bypassed the gate | ? UNCERTAIN (accepted as human-verify) | 153-03-SUMMARY.md records "User's literal response: 'Proceed — tag and push v5.12.0' (via AskUserQuestion selection)" and states the step ran in the foreground orchestrator session, not a dispatched executor — this class of claim (an actual human interaction transcript) cannot be independently re-derived from the codebase; treated as the CONTEXT.md-mandated human checkpoint, consistent with all downstream evidence (correct SHA tagged, no premature tag existed before this plan ran) |
| 7 | `v5.12.0` is tagged and pushed to `origin`, pointing at the version-bump commit | ✓ VERIFIED | `git ls-remote --tags origin v5.12.0` → `83ac92d993b018e67b1f6a568251bedc9cc14188 refs/tags/v5.12.0`; matches the SHA in truth #1 |
| 8 | The **real, tag-triggered** (`event: push`, not `workflow_dispatch`) `release.yml` run concludes success, including a passing signing self-test on the live tag | ✓ VERIFIED | `gh run view 31796819468 --json event,headBranch,conclusion` → `{"conclusion":"success","event":"push","headBranch":"v5.12.0"}` — independently re-queried, matches SUMMARY's claimed run ID exactly |
| 9 | The "Attach zip to GitHub Release" step actually ran (not skipped) and the `publish` (PyPI) job succeeded | ✓ VERIFIED | GitHub Release `v5.12.0` carries the asset (see #10); `curl https://pypi.org/pypi/quirk-scanner/json` independently confirms `info.version == "5.12.0"` is live on PyPI — both only happen if those gated steps ran for real |
| 10 | The GitHub Release for v5.12.0 carries a downloadable `quirk-windows-5.12.0.zip` asset | ✓ VERIFIED | `gh release view v5.12.0 --json assets,tagName,isDraft` independently re-run: `tagName: v5.12.0`, `isDraft: false`, asset `quirk-windows-5.12.0.zip`, size `58170009` bytes, `state: uploaded` |
| 11 | `python scripts/release_tag_hygiene.py` places `v5.12.0` in the OK bucket, not FLAGGED, with no edit to the baseline file | ✓ VERIFIED | `.venv/bin/python scripts/release_tag_hygiene.py` independently re-run: `v5.12.0` listed under `### OK (backed by a successful release run)`, "No flagged tags."; `git status --porcelain .github/tag-hygiene-baseline.txt` → empty (bare python without the venv's editable install errors — documented local-env quirk, not a bug; `.venv/bin/python` is the correct invocation) |
| 12 | `docs/UAT-SERIES.md` carries a Series 153 entry (Human-live shape) documenting RELEASE-01's live-fire proof, and the file is internally consistent (no orphaned/duplicate Notes lines from the insertion) | ✓ VERIFIED | `grep -n "Series 153: Release Tag Cut"` present; UAT-153-01 entry read in full — matches the UAT-144-03 template shape, cites real run IDs/URLs/SHAs, honestly documents the 153-04 deviation (dropped push-event trigger) rather than a clean narrative; **the WR-01 review defect (UAT-152-03's Notes line orphaned) is confirmed FIXED**: UAT-152-03 now ends correctly with `**Notes:** DISC-11...`, the file's tail ends cleanly with only UAT-153-01's own Notes block (`grep -c "DISC-11"` → 4 total occurrences project-wide, exactly 1 in the UAT-152-03 entry, 0 duplicated at file end) |
| 13 | Obsidian phase note + vault UAT-Series.md sync exist per CLAUDE.md's Mandatory Phase Completion Steps | ✓ VERIFIED | `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-153-Release-Tag-Cut.md` exists, `status: complete`, cites RELEASE-01 4×; `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` exists and contains "Series 153: Release Tag Cut" |

**Score:** 12/13 truths verified (1 accepted as an inherently human-verify claim, consistent with all surrounding evidence)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | `version = "5.12.0"` | ✓ VERIFIED | Confirmed live |
| `README.md` | `# QU.I.R.K. — v5.12.0` | ✓ VERIFIED | Confirmed live |
| `docs/UAT-SERIES.md` | Version literals + Series 153 entry, internally consistent | ✓ VERIFIED | Confirmed live, WR-01 fix confirmed applied |
| `docs/release-notes/5.12.0.md` | Milestone release notes | ✓ VERIFIED | Full structure present |
| `v5.12.0` git tag (origin) | Points at version-bump commit | ✓ VERIFIED | `git ls-remote --tags origin v5.12.0` |
| GitHub Release `v5.12.0` | `quirk-windows-5.12.0.zip` asset | ✓ VERIFIED | 58,170,009 bytes, uploaded |
| PyPI `quirk-scanner==5.12.0` | Published package | ✓ VERIFIED | Live on pypi.org |
| `/Users/digs/vaults/.../Phase-153-Release-Tag-Cut.md` | Obsidian phase note, `status: complete` | ✓ VERIFIED | Confirmed on filesystem |
| `/Users/digs/vaults/.../UAT-Series.md` | Vault sync of UAT-SERIES.md | ✓ VERIFIED | Confirmed, contains Series 153 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `origin/main` @ `83ac92d` | Python CI / Dashboard Quality / Staleness Gate | `push` event | ✓ WIRED | All 3 `success` on that exact SHA (independently re-queried) |
| `gh workflow run release.yml --ref main` | `windows-package` job, self-test | `workflow_dispatch` | ✓ WIRED | Independently re-confirmed success, publish job `skipped` |
| `refs/tags/v5.12.0` push (standalone, corrected) | `release.yml` `push` trigger | GitHub Actions push-event trigger | ✓ WIRED | Run `31796819468`, `event: push`, `success` — independently re-confirmed |
| `release.yml` Attach-zip step | GitHub Release `v5.12.0` assets | `softprops/action-gh-release` | ✓ WIRED | Asset present and downloadable, independently re-confirmed |
| `gh release list` / `gh run list` | `scripts/release_tag_hygiene.py evaluate_tags()` | `gh` CLI wrapped by the script | ✓ WIRED | `v5.12.0` in OK bucket, independently re-run via `.venv/bin/python` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Tag exists on remote at correct SHA | `git ls-remote --tags origin v5.12.0` | `83ac92d...` matches | ✓ PASS |
| Real tagged release.yml run is `event: push` and `success` | `gh run view 31796819468 --json event,conclusion` | `push` / `success` | ✓ PASS |
| GitHub Release carries the Windows zip | `gh release view v5.12.0 --json assets` | `quirk-windows-5.12.0.zip`, 58,170,009B | ✓ PASS |
| Tag-hygiene guard clean | `.venv/bin/python scripts/release_tag_hygiene.py` | `v5.12.0` under OK, zero flagged | ✓ PASS |
| PyPI carries the published version | `curl pypi.org/pypi/quirk-scanner/json` | `"version": "5.12.0"` | ✓ PASS |
| Six-surface version parity | `.venv/bin/pytest tests/test_version.py -q` | `6 passed, 1 deselected` | ✓ PASS |
| `docs/UAT-SERIES.md` internal consistency after WR-01 fix | `grep`/manual read of UAT-152-03 and file tail | UAT-152-03 Notes restored, no duplicate at tail | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RELEASE-01 | 153-01..05 | Cutting a release tag produces a Windows operator zip attached to the GitHub Release, proven on a real tagged CI run | ✓ SATISFIED | Real tag-triggered `release.yml` run `31796819468` (`event: push`) succeeded; GitHub Release `v5.12.0` carries `quirk-windows-5.12.0.zip`; both independently re-verified live, not read from SUMMARY prose alone |

`.planning/REQUIREMENTS.md` still shows RELEASE-01 as `Pending`/unchecked — this is expected at
this point in the workflow (the phase-close commit, which flips REQUIREMENTS.md/ROADMAP.md/
STATE.md, has not run yet; that is the orchestrator's next step after this verification passes).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found in the 4 files this phase touched (`pyproject.toml`, `README.md`, `docs/UAT-SERIES.md`, `docs/release-notes/5.12.0.md`) — no TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER strings | Info | 153-REVIEW.md's own quick-depth scan agrees; independently re-grepped, zero hits |

Two items surfaced during 153-REVIEW.md are addressed:
- **WR-01** (UAT-152-03 Notes-line corruption from the Series 153 insertion) — **confirmed fixed**
  in commit `f8b282e`, independently verified above (truth #12).
- **IN-01** (README's "What's New in v5.10" section heading is stale, pre-dates this phase) —
  confirmed pre-existing via `git show b0c99df:README.md`; correctly out of scope for this phase's
  diff; left as a backlog doc item per the review's own recommendation, not a Phase 153 gap.

### Human Verification Required

#### 1. Push the 3 local-only commits to `origin/main` before/at phase close

**Test:** Run `git rev-list --left-right --count origin/main...HEAD` from the repo root.
**Expected:** `0	0` — local `main` and `origin/main` are in sync.
**Why human:** Currently local `main` is **3 commits ahead of `origin/main`**:
`879f755` (docs(153): UAT-SERIES.md Series 153 entry), `035c24d` (its --no-ff merge), and
`f8b282e` (the WR-01 review fix). None of these affect the already-proven RELEASE-01 evidence —
the tag, the tagged CI run, the GitHub Release asset, and the PyPI publish all trace to `83ac92d`,
which **is** on `origin` and was the exact SHA tagged. This is a docs-only staleness gap between
local and remote, not a defect in the release pipeline. Whether to push now or fold it into the
phase-close sequence is an operator call (`git push origin main`), not something a grep can decide
for the user — flagging per this project's own convention (docs/vault sync + `gsd-tools.cjs
commit` steps assume eventual push to the public remote).

#### 2. Confirm the tag-push human-confirmation checkpoint was answered by an actual human

**Test:** Recall/confirm whether you (Digs) personally typed/selected "Proceed — tag and push
v5.12.0" via the AskUserQuestion prompt described in `153-03-SUMMARY.md`.
**Expected:** Yes — a real, attended approval was given before `git tag v5.12.0` ran.
**Why human:** `153-CONTEXT.md` locks this as a mandatory human-in-the-loop gate specifically
because GSD's autonomous auto-chain would silently auto-select "proceed." A verifier operating
only against the codebase cannot distinguish a genuinely human-attended AskUserQuestion response
from one an unattended process could theoretically have triggered; all downstream evidence (single
tag creation event, correct SHA, no premature push) is consistent with the SUMMARY's claim, but
the interaction itself is not independently re-derivable from repository state.

### Gaps Summary

No FAILED must-haves. All release-pipeline, tag, asset, and hygiene-guard claims were
independently re-verified against live GitHub/PyPI state, not trusted from SUMMARY.md prose — in
every case the SUMMARY's claimed run IDs, SHAs, and asset details matched a fresh `gh`/`curl`/
`pytest` query run during this verification. One real defect from code review (WR-01, UAT-SERIES
Notes-line corruption) was confirmed genuinely fixed. The only open items are (1) an operational
housekeeping gap — 3 local commits not yet pushed to `origin/main` — which does not affect the
RELEASE-01 proof itself since that proof lives entirely on the already-pushed `83ac92d` SHA, and
(2) the inherent human-attendance question on the tag-push checkpoint, which no static check can
resolve. Neither is a FAILED must-have; both are routed to human sign-off per the Escalation Gate
pattern.

---

_Verified: 2026-08-14T11:50:00Z_
_Verifier: Claude (gsd-verifier)_
