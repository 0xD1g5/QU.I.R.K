# v5.11 Phase Archive — PARTIAL (incident record)

**Created:** 2026-08-11
**Status:** ⚠️ Incomplete — approximately 39 of ~58 phase artifact files were permanently lost.

## What happened

During `/gsd-new-milestone` (opening v5.12), workflow step 6 calls:

```bash
gsd-sdk query phases.clear --confirm
```

This **deletes** `.planning/phases/*` rather than archiving it. The archival step that should
have preceded it — the "Archive Phases" prompt inside `milestone.complete` — was never run;
`milestone.complete` had reported `"archived": {"phases": false}` at v5.11 close, and the clear
was executed without checking that flag first.

Because `.planning/` is gitignored, only the small subset of phase files that had been
force-added to git at some point survived. `git checkout -- .planning/phases/` recovered those
19 files; the rest were untracked and are unrecoverable (not in `~/.Trash`, not moved, no copy
elsewhere on disk).

## What survived (19 files, in this directory)

| Phase | Files recovered | Of original | Notes |
|-------|-----------------|-------------|-------|
| 144 Chunked Discovery Core | **0** | 13 | **Directory lost entirely** |
| 145 Liveness Pre-Pass | 12 | 12 | ✅ Complete — was fully tracked |
| 146 Progress, Scaling & Disclosure | 1 | 19 | Only `146-03-SUMMARY.md` |
| 147 Backlog Drain | 6 | 14 | SUMMARYs 01/02/04, CONTEXT, DISCUSSION-LOG, VALIDATION |

## What was lost

- **Phase 144 (all):** `144-01/02/03-PLAN.md` + `-SUMMARY.md`, `144-CONTEXT.md`,
  `144-DISCUSSION-LOG.md`, `144-PATTERNS.md`, `144-RESEARCH.md`, `144-VALIDATION.md`,
  `144-VERIFICATION.md`, `deferred-items.md`
- **Phase 146:** all PLANs (01–06), SUMMARYs 01/02/04/05/06, `146-CONTEXT.md`,
  `146-RESEARCH.md`, `146-PATTERNS.md`, `146-REVIEW.md`, `146-VALIDATION.md`,
  `146-VERIFICATION.md`
- **Phase 147:** `147-01/02/03-PLAN.md`, `147-03-SUMMARY.md`, `147-PATTERNS.md`,
  `147-RESEARCH.md`, `147-VERIFICATION.md`

## What the lost content is still recoverable *from*

The raw per-plan artifacts are gone, but the **decision record is substantially preserved** —
largely because the v5.11 milestone audit and closeout had just quoted them extensively:

| Lost content | Where it survives |
|--------------|-------------------|
| Phase 144/146/147 VERIFICATION findings, criteria, evidence | `.planning/milestones/v5.11-MILESTONE-AUDIT.md` (quotes goal-achievement tables, override text, file:line evidence) |
| Phase 144 `deferred-items.md` (nmap timing root cause) | Quoted in full in `v5.11-MILESTONE-AUDIT.md` tech-debt block, `.planning/STATE.md`, and ROADMAP Backlog |
| Phase 146 `146-REVIEW.md` CR-01/WR-01/WR-02/IN-01 | Full dispositions in `v5.11-MILESTONE-AUDIT.md` § Code Review Disposition |
| Per-plan accomplishments and one-liners | `.planning/MILESTONES.md` v5.11 entry (hand-curated) + the four Obsidian phase notes at `20_Dev-Work/QUIRK/Phases/Phase-14{4,5,6,7}-*.md` |
| Full phase goals, success criteria, plan lists | `.planning/milestones/v5.11-ROADMAP.md` (37 KB, complete) |
| UAT detail for all four phases | `docs/UAT-SERIES.md` Series 144–147 (tracked in git, unaffected) |
| Key decisions | `.planning/PROJECT.md` Key Decisions, `.planning/STATE.md` Accumulated Context, `.planning/RETROSPECTIVE.md` v5.11 section |

**Code is unaffected.** Every commit, test, and source change from v5.11 is intact in git
history and on `origin/main`.

## Prevention

This is a v5.12 candidate in its own right, and it is the same failure class the milestone was
opened to address — a destructive step running without verifying the precondition it depends on:

1. `phases.clear` should refuse to run when the current milestone's
   `.planning/milestones/v<X.Y>-phases/` archive is absent or empty.
2. The `milestone.complete` `"archived": {"phases": false}` flag should be checked by the
   `new-milestone` workflow before step 6, not ignored.
3. `.planning/` being gitignored while partially force-added means git is not a reliable
   safety net here — either commit phase artifacts consistently or archive before clearing.
