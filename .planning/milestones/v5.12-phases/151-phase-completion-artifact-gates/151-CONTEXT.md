# Phase 151: Phase-Completion Artifact Gates - Context

**Gathered:** 2026-08-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase closes the exact gap that let three of four v5.11 phases ship without a completion
artifact and let `phases.clear` delete ~39 unrecoverable v5.11 phase files: it builds QUIRK-repo-local
enforcement (not a fork or modification of the global GSD tooling) that (1) blocks a phase-closing
commit when `VERIFICATION.md` is missing, `VALIDATION.md` is stale, or a user-facing phase lacks a
`docs/UAT-SERIES.md` entry, and (2) blocks a destructive commit that would delete `.planning/phases/*`
content without a matching milestone archive manifest.

</domain>

<decisions>
## Implementation Decisions

### Enforcement layer (critical technical constraint)
- **D-01:** `.planning/` is entirely gitignored on this public repo (`.gitignore:67`, confirmed via
  `git check-ignore`), per the Phase 120 PUBREPO-01 policy. CI's checkout never contains it. This
  makes a CI-based meta-gate test (the initially-proposed approach, modeled on
  `tests/test_skip_registry.py`) structurally incapable of enforcing ARTIFACT-01/02/03 — it would
  find zero phase directories in Actions and enforce nothing. All four ARTIFACT gates MUST be
  enforced as a **local git hook**, which is the only point in the workflow where `.planning/` still
  exists on disk before a commit strips visibility of it.
- **D-02:** ARTIFACT-01/02/03 (phase-close checks) and ARTIFACT-04 (destructive-deletion guard) are
  ONE shared hook script — `scripts/verify_phase_gates.py` — with two check functions (e.g.
  `check_phase_close()` and `check_destructive_archive()`), both wired into the same pre-commit hook
  entry point. Single source of truth, avoids two near-identical hook files, matches this repo's
  existing single-purpose-script-per-concern convention (`scripts/release_tag_hygiene.py`) at the
  file level while keeping the two concerns logically separate as functions.
- **D-03:** The hook triggers ONLY on phase-closing commits, not every commit. Detection: `STATE.md`
  and `ROADMAP.md` ARE git-tracked (unlike `.planning/phases/`, confirmed — they predate the Phase 120
  gitignore rule and remain committable). The hook inspects the staged diff to `STATE.md`/`ROADMAP.md`
  for a phase status flip to `Complete`; only when that fires does it read the corresponding
  `.planning/phases/<N>-*/` directory on disk and run the artifact checks. Cheap on unrelated commits.
- **D-04:** ARTIFACT-04's mechanism: `phases.clear` (or any equivalent destructive GSD operation) is
  NOT modified — that would be rewriting GSD tooling, explicitly out of scope. Instead the hook is
  tool-agnostic: it inspects the staged diff for deletions under `.planning/phases/*` (or an
  equivalent working-tree state change the hook can detect) and blocks the commit unless a matching
  `.planning/milestones/v<X.Y>-phases/ARCHIVE-MANIFEST.md` exists for the current milestone. Works
  regardless of which command performed the deletion.

### ARTIFACT-03 "user-facing" heuristic
- **D-05:** The hook decides whether a phase "shipped user-facing behavior" (and therefore needs a
  `docs/UAT-SERIES.md` entry) via a **files_modified path heuristic**, not an explicit opt-out flag.
  Scan each plan's `PLAN.md` `files_modified` frontmatter for paths matching user-facing surfaces:
  `src/dashboard/**`, CLI entry points (`quirk/cli/**` or equivalent), report-renderer files adjacent
  to `docs/report-interpretation.md`'s subject matter, new scanner/detector modules. If any plan in
  the phase matches, require a `docs/UAT-SERIES.md` entry citing the phase. Pure-internal paths
  (`tests/`, `scripts/`, `.github/`, docs-only changes) do not trigger the requirement.

### Retroactive scope
- **D-06:** Future-only — no backfill. The gate prevents recurrence going forward from this phase.
  The three historical v5.11 gaps (Phase 145 missing VERIFICATION.md, Phase 147's stale VALIDATION.md,
  Phase 144 shipping without a UAT-SERIES.md entry) stay as-is: 145/147 already got VERIFICATION.md
  written retroactively at the v5.11 audit closeout per STATE.md's Decisions log, and Phase 144's
  missing UAT-SERIES.md entry is treated as a closed, accepted historical fact — not something this
  phase's scope extends to fixing.

### Claude's Discretion
- Exact `STATE.md`/`ROADMAP.md` diff-parsing approach (regex vs. structured parse) for detecting a
  phase-close status flip in D-03.
- Exact hook installation mechanism (`core.hooksPath` pointing at a checked-in `.githooks/` dir vs. a
  `pre-commit` framework config) — whichever matches how contributors are expected to set up the repo
  per `CONTRIBUTING.md` (Phase 150 already added a CONTRIBUTING.md; check its conventions before
  choosing).
- Whether `VALIDATION.md` staleness detection (ARTIFACT-02: pending rows, `nyquist_compliant: false`)
  parses the file as YAML frontmatter + markdown checklist, or does a targeted grep/regex — the
  planner/researcher should check `VALIDATION.md`'s actual on-disk shape before deciding.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The three incidents this phase closes
- `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md` — the exact `phases.clear` incident
  (2026-08-11) that deleted ~39 unrecoverable v5.11 phase files after `milestone.complete` reported
  `archived.phases: false` with nothing gating on it. ARTIFACT-04's acceptance criteria cite this
  file directly.
- Phase 145 (`.planning/milestones/v5.11-phases/145-liveness-pre-pass/`) — the missing-VERIFICATION.md precedent for
  ARTIFACT-01.
- Phase 147 (`.planning/milestones/v5.11-phases/147-backlog-drain-lifecycle-ledger-tail/`) — the stale-VALIDATION.md precedent for ARTIFACT-02.
- Phase 144 (`.planning/phases/144-*/`) — the missing-UAT-SERIES.md-entry precedent for ARTIFACT-03.

### Existing repo conventions to follow
- `scripts/release_tag_hygiene.py` + `tests/test_release_tag_hygiene.py` +
  `.github/workflows/release-tag-hygiene.yml` — the closest existing precedent for a QUIRK-local
  guard script with its own test, though that one is CI-triggered (works because tags/commits ARE
  visible to CI); this phase's script is git-hook-triggered instead, per D-01.
- `tests/skip_registry.py` + `tests/test_skip_registry.py` — the existing "meta-gate" pattern (an
  AST/structural walker that fails if a convention is violated), useful as a design reference for
  `check_phase_close()`'s artifact-presence logic even though it won't run via this exact CI
  mechanism.
- `CONTRIBUTING.md` (added in Phase 150-02) — check for any existing hook-setup instructions before
  choosing the installation mechanism (Claude's Discretion above).
- `CLAUDE.md`'s "Mandatory Phase Completion Steps" section — the human-authored checklist this
  automated gate is meant to backstop, not replace.

### Requirements
- `.planning/REQUIREMENTS.md` — ARTIFACT-01 through ARTIFACT-04 full text (lines 60-75) and the
  explicit Out-of-Scope row: "Rewriting the GSD tooling itself | ARTIFACT-01..04 are enforcement gates
  on QUIRK's own workflow, not a fork or reimplementation of GSD."
- `.planning/ROADMAP.md` (Phase 151 section, ~line 233) — Goal, 4 numbered Success Criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None directly reusable (no existing git-hook infrastructure in this repo — `.claude/hooks/` and
  `.git/hooks/pre-commit` were both confirmed absent during discussion). This is genuinely new
  infrastructure for the project.

### Established Patterns
- Single-purpose Python script + matching pytest test file, invoked by a workflow, is the dominant
  QUIRK convention for guard/gate logic (`release_tag_hygiene.py`, `hw_cve.py`'s staleness check,
  `qramm/model_meta.py`'s staleness check). `scripts/verify_phase_gates.py` should follow this shape.
- `STATE.md` and `ROADMAP.md` are the only two `.planning/` files that survive the Phase 120
  gitignore rule (tracked from before the rule existed) — this is the load-bearing fact that makes
  D-03's diff-detection approach possible at all.

### Integration Points
- Git hook installation: needs a checked-in hook script (e.g. `.githooks/pre-commit` +
  `git config core.hooksPath .githooks`, documented in `CONTRIBUTING.md`) since `.git/hooks/` itself
  is never committed.
- The hook's `check_phase_close()` reads `.planning/phases/<N>-*/` directly off disk — it must run
  from the repo root with the working tree in its normal (non-worktree) state; no interaction with
  the worktree-isolation execution mode expected (worktrees are disabled project-wide per
  `workflow.use_worktrees: false`).

</code_context>

<specifics>
## Specific Ideas

No specific UI/UX or output-format preferences surfaced — this phase is pure tooling/enforcement, not
user-facing product work. Discussion focused entirely on mechanism (where enforcement lives) given the
gitignored-`.planning/` constraint that invalidated the initially-assumed CI-based approach.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 151-Phase-Completion Artifact Gates*
*Context gathered: 2026-08-13*
