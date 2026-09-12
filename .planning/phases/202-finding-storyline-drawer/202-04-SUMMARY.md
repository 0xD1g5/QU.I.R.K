---
phase: 202-finding-storyline-drawer
plan: 04
subsystem: ui
tags: [react, vitest, tailwind, shadcn, storyline-drawer, score-lift-attribution]

requires:
  - phase: 202-02
    provides: FindingStoryline TS type (10 fields, zero optionals) and useFindingStoryline hook (error separate from absence)
provides:
  - StorylineSections component covering all 8 UI-SPEC State Matrix rows (S1-S6, S8; S7 non-applicable)
  - Mechanical enforcement of Invariants 1-3 (single-node lift condition, disclaimer co-presence, division trip-wire)
  - formatScoreNumber 4.27 -> +4.3 regression coverage (201-UI-E5)
affects: [202-06]

tech-stack:
  added: []
  patterns:
    - "Attribution panel branch precedence: theme_slug==null -> A1; else theme_finding_count==null||===0 -> A3; else theme_score_lift==null -> A2; else full lift sentence + disclaimer"
    - "Position/closure sentences are independently gated sub-components (PositionSentence/ClosureSentence), never a combined line"

key-files:
  created:
    - src/dashboard/src/components/FindingStorylineSections.tsx
    - src/dashboard/src/components/__tests__/finding-storyline-sections.test.tsx
  modified: []

key-decisions:
  - "Disclaimer copy uses &apos; HTML entities for apostrophes (matching schedules.tsx:291's existing convention) rather than raw apostrophes; renders identical text at runtime, verified in the vitest getByText transcript"
  - "AttributionPanel returns null when data is null in the non-loading, non-error branch (an unenumerated state outside the 8-row State Matrix, defensive only)"

requirements-completed: [STORY-01, STORY-02]

duration: ~45min
completed: 2026-09-12
---

# Phase 202 Plan 04: StorylineSections Component Summary

**`StorylineSections` component implementing all 8 UI-SPEC states with a mechanically-enforced division trip-wire proving `theme_score_lift` is never divided by any count**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments

- `FindingStorylineSections.tsx` (246 lines) exports `StorylineSections`, covering narrative section, attribution block (rendered last as a bordered panel, never a header chip), and loading/error states for State Matrix rows S1-S6 and S8 (S7 never mounts this component per the UI-SPEC — trigger is disabled upstream)
- Invariant 1 satisfied structurally: the accented `+N` `<span>` and its `pts when all N findings...` condition clause share one `<p>` with no intervening block-level element
- Invariant 2 (disclaimer co-presence) and Invariant 3 (division trip-wire) both mechanically enforced by `finding-storyline-sections.test.tsx` (28 tests, 26 passed + 2 explicit S7 skips)
- A5 (no narrative) built as real, first-class copy per D-07 — independent of the attribution panel, which stays fully populated (S6)
- 4.27 -> `+4.3` and 4 -> `+4` formatting regressions in place (201-UI-E5)

## Task Commits

1. **Task 1: StorylineSections — narrative section, attribution block, loading and error states** - `77eafc97` (feat)
2. **Task 2: Eight-state parametrised tests, Invariants 1-3, and the 4.27 formatting regression** - `37bfa6ce` (test)

**Plan metadata:** `573ca5c7` (docs: flip 202-VALIDATION.md rows 202-04-T1/T2 to green)

_Note: this is a single RED->GREEN cycle per the plan's TDD instruction — the test file was authored against the already-complete Task 1 implementation, then a live division-mutation was injected and reverted to produce a genuine RED transcript for Invariant 3 specifically (see below), since a from-scratch stub-first RED run was not separately recorded as its own commit._

## How Invariant 1 was asserted (pasted assertion)

```tsx
const paragraphs = Array.from(container.querySelectorAll("p"))
const liftParagraph = paragraphs.find(
  (p) => /\+\d/.test(p.textContent ?? "") && /when all/.test(p.textContent ?? ""),
)
expect(liftParagraph).toBeTruthy()
expect(liftParagraph!.tagName).toBe("P")

const span = liftParagraph!.querySelector("span")
expect(span).toBeTruthy()
expect(span!.textContent).toMatch(/^\+4$/)

const ancestor = nearestBlockAncestor(span!)  // walks parentElement, checking a BLOCK_TAGS set
expect(ancestor).toBe(liftParagraph)
```

`nearestBlockAncestor` walks `parentElement` from the span, checking tag name against a `BLOCK_TAGS` set (`DIV`, `P`, `SECTION`, etc.), and returns the first block-level ancestor found. Asserting that ancestor `=== liftParagraph` proves the span's nearest block ancestor is the `<p>` itself — no `<div>`/`<br>`/grid cell sits between them.

## Division trip-wire result

Rendered with `theme_score_lift: 7, theme_finding_count: 2` (position/closure nulled to avoid an incidental `3` in the panel):

```ts
expect(panel.textContent).toContain("7")
expect(panel.textContent).toContain("2")
expect(panel.textContent).not.toContain("3.5")
expect(panel.textContent).not.toMatch(/\b3\b/)
```

**Live falsification run (RED transcript):** temporarily mutated the source to
`+{formatScoreNumber(theme_score_lift / theme_finding_count)}` (7/2 = 3.5) and reran the suite:

```
 ❯ src/components/__tests__/finding-storyline-sections.test.tsx (28 tests | 7 failed | 2 skipped)
   × StorylineSections — Invariant 3 (division trip-wire) > lift 7 / count 2 renders 7 and 2, and NEITHER 3.5 NOR 3 appears anywhere in the panel
     → expected 'Score-lift attributionRemediation the…' to contain '7'
   × StorylineSections — Number Formatting Contract (201-UI-E5 regression) > theme_score_lift: 4.27 renders exactly '+4.3 pts when all 8 findings in this theme are resolved'
   × StorylineSections — Number Formatting Contract (201-UI-E5 regression) > theme_score_lift: 4 renders '+4', not '+4.0'
   ... (7 failed | 19 passed | 2 skipped)
```

Reverted the mutation (`cp` from a pre-mutation backup) and reran — back to `26 passed | 2 skipped`, zero diff on the component file. This proves the trip-wire test fails on a real division and passes only on the honest implementation.

## Vitest counts before/after

- **Before this plan:** `finding-storyline-sections.test.tsx` did not exist (0 tests)
- **After this plan:** 28 tests defined, 26 passed, 2 skipped (both are the S7 "not applicable" skip, one in the State Matrix describe block and one in the Invariant 2 describe block, each naming 202-06 as where S7 is covered)

## Ten-string `grep -F` copy transcript

```
$ grep -F "Storyline" FindingStorylineSections.tsx        # narrative + narrative label
$ grep -F "Score-lift attribution" ...                    # attribution label
$ grep -F "Remediation theme: " ...                        # theme line prefix
$ grep -F "pts when all " ...                              # lift sentence
$ grep -F "in the theme are resolved" ...                  # lift sentence tail
$ grep -F "This finding is " ...                            # position sentence
$ grep -F "findings in this theme are verified closed." ... # closure sentence
$ grep -F "Not mapped to a remediation theme" ...           # A1
$ grep -F "Score lift could not be modelled" ...            # A2
$ grep -F "No catalog narrative exists for this finding type yet" ... # A5
$ grep -F "Loading storyline…" ...                          # loading sr-only text
$ grep -F "Retry storyline" ...                             # error button label
```
All matched. Note: the A3 string (`"The theme's constituent findings could not be counted..."`) and the disclaimer string use `&apos;` HTML entities for the apostrophe in source (matching `schedules.tsx:291`'s existing convention), so a literal-apostrophe `grep -F` on the raw source text will not match — the rendered DOM text is byte-identical to the UI-SPEC copy, confirmed by the vitest `getByText` assertions against the exact strings (with real apostrophes) passing.

## Source-gate grep results

```
$ npx tsc --noEmit && npm run lint   # both exit 0
$ grep -nE "theme_score_lift\s*/|/\s*theme_finding_count|/\s*theme_closed_count|toFixed|Math\.round|toLocaleString" FindingStorylineSections.tsx
  (no matches)
$ grep -nE "gap-1\.5|ml-1\.5|mt-1\.5|-mt-0\.5|space-y-2\.5|p-1\.5|-\[[0-9]+px\]" FindingStorylineSections.tsx
  (no matches)
$ grep -nE "#[0-9a-fA-F]{3,6}|rgb\(|hsl\(" FindingStorylineSections.tsx
  (no matches)
=> SOURCE_GATES_OK
$ grep -c "var(--ds-ok)" FindingStorylineSections.tsx   => 1
$ grep -c "fontSize: 20" FindingStorylineSections.tsx   => 1
$ grep -c "dangerouslySetInnerHTML" FindingStorylineSections.tsx => 0
$ git status --short quirk/dashboard/static             => (empty)
```

## Files Created/Modified

- `src/dashboard/src/components/FindingStorylineSections.tsx` — `StorylineSections` component, 246 lines
- `src/dashboard/src/components/__tests__/finding-storyline-sections.test.tsx` — 28-test suite, 361 lines

## Decisions Made

- Apostrophes in copy strings use `&apos;` HTML entities per the existing `schedules.tsx:291` convention (not a deviation — matches established codebase style for JSX text nodes containing possessive apostrophes).
- `AttributionPanel` short-circuits to `null` when `data` is `null` outside the loading/error branches — a state combination the 8-row State Matrix does not enumerate (loading `false`, error `null`, data `null` should not occur given the hook's contract, but the guard avoids a runtime crash rather than assuming the caller never produces it).

## Deviations from Plan

None — plan executed as written. Per this plan's own explicit instruction (`.tsx` edits require `npm run lint && npm run test` from `src/dashboard/`, with **no** `npm run build` and **no** statics commit — 202-06 owns the rebuilt statics), no build was run and no `quirk/dashboard/static` diff exists, verified explicitly above.

## Issues Encountered

- Initial test draft's `panel.querySelector("span")` picked up the wrong `<span>` (the "Remediation theme: " prefix span, not the accented lift span) in the `4 -> +4` formatting test. Fixed by scoping the query with a `/^\+/` textContent filter across all spans in the panel. This was caught and fixed before any commit — not a deviation from the plan, a normal TDD debugging step.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

`StorylineSections` is fully self-contained and ready for 202-06 to mount inside the extended `Sheet`. 202-06 must additionally implement: the `Storyline` trigger column (F1), the A6 disabled-trigger state (S7, explicitly skipped here), the responsive `SheetContent` width/scroll changes, and the full focus contract (F1-F9) — none of which this plan's component touches.

---
*Phase: 202-finding-storyline-drawer*
*Completed: 2026-09-12*

## Self-Check: PASSED

- FOUND: `src/dashboard/src/components/FindingStorylineSections.tsx`
- FOUND: `src/dashboard/src/components/__tests__/finding-storyline-sections.test.tsx`
- FOUND commit `77eafc97` (Task 1)
- FOUND commit `37bfa6ce` (Task 2)
- FOUND commit `573ca5c7` (VALIDATION.md flip)
