# Phase 153: Release Tag Cut - Context

**Gathered:** 2026-08-13
**Status:** Ready for planning
**Mode:** Infrastructure phase — smart-discuss skipped (all success criteria are technical: CI job
completion, asset attachment, guard pass/fail, artifact existence; no user-facing behavior
described)

<domain>
## Phase Boundary

Cutting the real `v5.12.0` git tag and pushing it proves every signal this milestone repaired
(Phase 148's release pipeline, Phase 150's CI gate, Phase 151's artifact gates applied to this
very phase) end-to-end on an actual immutable tag — not a dry run. Out of scope: any further
scanner feature work, any change to the release pipeline mechanics themselves (those were fixed
in Phase 148 and are being *used*, not modified, here).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Exact plan/task breakdown for pre-tag checks (tag-hygiene guard dry-run, full test suite green,
  version string consistency) vs. the tag-push-and-verify step itself — follow whatever shape the
  planner and researcher find cleanest, informed by Phase 148's existing dry-run mechanism and
  tag-format guard.
- Exact wording/structure of Phase 153's own VERIFICATION.md / VALIDATION.md / UAT-SERIES.md entry
  — this phase deliberately dogfoods Phase 151's own gates on itself (Success Criterion 4), so
  follow the same shape those gates expect.

### Locked — not discretionary, applies regardless of plan content
- **The actual `git tag v5.12.0` + `git push origin v5.12.0` step (and any GitHub Release
  creation/publish step) is a hard-to-reverse, externally-visible action.** Per standing operating
  guidance, this requires an explicit pause for user confirmation before it runs, regardless of
  what a PLAN.md task says or how confident an executor is. Pre-tag verification (dry-run,
  version-string checks, full suite green) can and should run freely without a pause — only the
  actual tag/release creation step itself is gated.
- **OPERATIONAL CONSTRAINT — foreground-only execution for the tag-push step:** Plan 153-03's
  tag-push task MUST NEVER be run via `/gsd:autonomous` or any other auto-chained/background
  execution path. GSD's own `checkpoint:decision` auto-approves its first option when auto-mode is
  active (see `~/.claude/get-shit-done/workflows/execute-phase.md`'s checkpoint_handling step and
  `~/.claude/get-shit-done/references/checkpoints.md` Golden Rule 5), and Plan 153-03 Task 1's
  first option is "proceed" — meaning an auto-mode run could silently tag and push `v5.12.0`
  without any human ever seeing the decision. Plan 153-03 must only be executed via direct,
  foreground orchestration where a human explicitly confirms immediately before the
  `git tag`/`git push --tags`/release-create commands run. This mirrors Phase 120's go-public flip,
  which was run with explicit checkpoints and never via `/gsd-autonomous`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 148's pre-tag dry-run mechanism (`workflow_dispatch` exercising `windows-package` without
  a real tag) and tag-format guard — this phase *uses* both, does not modify them.
- `scripts/verify_phase_gates.py` (Phase 151) — this phase's own close-out is the first real-world
  test of ARTIFACT-01/02/03 enforcement on a phase that ships them.

### Established Patterns
- `.github/workflows/release.yml` — the release pipeline this phase's tag push triggers.
- Prior release tags (`v5.11.0`, `v5.10.0`, etc.) — the existing tag/release naming and asset
  pattern to match for `v5.12.0`.

### Integration Points
- GitHub Actions `release.yml` windows-package job — triggered by the tag push.
- GitHub Releases page — where the Windows operator zip must land, downloadable.

</code_context>

<specifics>
## Specific Ideas

No specific implementation references beyond the locked tag-push confirmation gate above —
infrastructure phase, discuss skipped.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
</output>
