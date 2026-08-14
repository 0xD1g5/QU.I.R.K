---
phase: 153
slug: release-tag-cut
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-13
updated: 2026-08-14
---

# Phase 153 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing project standard) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `pytest tests/test_version.py -x` |
| **Full suite command** | `pytest -q` (Phase 150 confirmed green on CI parity venv) |
| **Estimated runtime** | RELEASE-01 itself is live-fire/manual — not pytest; supporting checks are fast |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_version.py -x` (targeted, after the version-bump task in 153-02)
- **After every plan wave:** `gh run list` / `gh run view` for the live CI evidence tasks (153-01, 153-04); `pytest -q` (full suite) is optional insurance since the real GitHub Actions run is the actual gate
- **Before `/gsd:verify-work`:** the live GitHub Actions `release.yml` run on the real `v5.12.0`
  tag push IS the phase gate for RELEASE-01 — no pytest substitute is acceptable
- **Max feedback latency:** N/A for the live-fire steps (external CI); 30s for supporting pytest checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 153-01-01 | 01 | 1 | RELEASE-01 (prereq) | T-153-02 | origin/main synced, real CI green on pushed SHA | live-fire CLI | `gh run list --branch main --limit 3 --json headSha,name,conclusion` | N/A | ✅ green |
| 153-01-02 | 01 | 1 | RELEASE-01 (prereq) | T-153-01 | workflow_dispatch dry-run green, self-test OK, zero publish side effects | live-fire CLI | `gh run list --workflow release.yml --limit 3 --json databaseId,event,conclusion` | N/A | ✅ green |
| 153-02-01 | 02 | 2 | RELEASE-01 (prereq) | T-153-04 | pyproject.toml sole canonical edit, six-surface parity holds | unit | `pytest tests/test_version.py -x -v` | ✅ | ✅ green |
| 153-02-02 | 02 | 2 | RELEASE-01 (prereq) | T-153-03 | manual literals updated, release notes written, clean explicit-path commit | CLI grep/git | `grep -c "5\.11\.0" README.md docs/UAT-SERIES.md` | ✅ | ✅ green |
| 153-03-01 | 03 | 3 | RELEASE-01 | T-153-05, T-153-06 | human explicitly approves before the irreversible tag push | checkpoint:decision (human) | N/A — locked human-confirmation gate, no automated substitute | N/A | ✅ green (approved via AskUserQuestion, twice — initial push + standalone re-push fix) |
| 153-03-02 | 03 | 3 | RELEASE-01 | T-153-06 | v5.12.0 tag created + pushed only after approval | CLI | `git ls-remote --tags origin v5.12.0` | N/A | ✅ green |
| 153-04-01 | 04 | 4 | RELEASE-01 | T-153-07, T-153-09 | tagged release.yml run (event=push) green, self-test OK, attach-zip step ran | live-fire CLI | `gh run list --branch main --limit 6 --json databaseId,workflowName,event,conclusion` | N/A | ✅ green (after one documented, human-approved recovery — see 153-04-SUMMARY.md) |
| 153-04-02 | 04 | 4 | RELEASE-01 | T-153-08 | GitHub Release carries Windows zip; tag-hygiene guard clean, no baseline edit | live-fire CLI | `gh release view v5.12.0 --json assets` / `python scripts/release_tag_hygiene.py` | ✅ | ✅ green |
| 153-05-01 | 05 | 5 | RELEASE-01 (dogfood) | T-153-10 | docs/UAT-SERIES.md Series 153 entry evidence-backed | CLI grep | `grep -n "Series 153: Release Tag Cut" docs/UAT-SERIES.md` | ✅ | ✅ green |
| 153-05-02 | 05 | 5 | RELEASE-01 (dogfood) | T-153-11 | Obsidian phase note + vault UAT-Series.md sync complete before phase-close commit | CLI test/grep | `test -f <vault phase note>` | N/A | ✅ green |
| (dogfood) | — | post-close | RELEASE-01 (dogfood) | — | Phase 153's own close commit passes ARTIFACT-01/02/03 | pre-commit hook | `.githooks/pre-commit` fires `scripts/verify_phase_gates.py` automatically | ✅ | ⚠️ NOT ENFORCED — `core.hooksPath` is not installed in this working copy, so the hook did not actually run against this phase's close commits. `scripts/verify_phase_gates.py` was run manually/simulated and passed for Phase 153's close, but this row's original claim ("automatically") was inaccurate — corrected during the v5.12 milestone integration check (2026-08-14). Installing the hook (`git config core.hooksPath .githooks`) is a documented, opt-in step per `CONTRIBUTING.md`, not yet exercised in this checkout. |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — existing test infrastructure (`tests/test_version.py`, `tests/test_release_tag_hygiene.py`)
and existing CI workflows (`release.yml`, `release-tag-hygiene.yml`, `release-container.yml`,
`python-ci.yml`) fully cover everything this phase needs to verify. No new test files required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real tagged `release.yml` run completes green with signing self-test passing | RELEASE-01 | Inherently an external CI proof — no local/pytest substitute is acceptable per this phase's own design (mirrors Phase 150's SUITE-02/03 "real CI run, not local" precedent) | Push `v5.12.0` (Plan 153-03, human-gated), watch the run via `gh run watch` (Plan 153-04), confirm `windows-package` job green and self-test output in logs |
| GitHub Release has downloadable Windows operator zip | RELEASE-01 | External GitHub state, not code-verifiable | `gh release view v5.12.0 --json assets` and confirm a Windows zip asset is listed (Plan 153-04 Task 2) |
| The tag/push itself | RELEASE-01 | Locked `153-CONTEXT.md` decision: hard-to-reverse, externally-visible action requires explicit human confirmation before it runs | Plan 153-03 Task 1, `checkpoint:decision`, blocking gate |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are the locked human-confirmation checkpoint (153-03 Task 1)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (153-03 Task 1 is the sole non-automated task, bracketed by automated-verify tasks on both sides)
- [x] Wave 0 covers all MISSING references (none — no new test files needed)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (pytest path); live-fire CI paths are inherently longer and documented as such
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-approved 2026-08-13; reconciled post-execution 2026-08-14 against real
live GitHub/PyPI state (independently re-verified by 153-VERIFICATION.md, not just SUMMARYs).
One row corrected for accuracy (the pre-commit-hook dogfood row) rather than falsely marked
green — see that row's note.
