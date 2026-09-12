---
phase: 202-finding-storyline-drawer
plan: 06
subsystem: dashboard-findings-page
tags: [a11y, focus-management, sheet, react, vitest]
dependency-graph:
  requires: ["202-02 (useFindingStoryline hook, FindingStoryline type)", "202-04 (StorylineSections component)"]
  provides: ["findings.tsx Storyline trigger column", "extended finding-detail Sheet", "F1-F9 focus contract"]
  affects: ["202-07 (a11y baseline capture opens this exact drawer)"]
tech-stack:
  added: []
  patterns:
    - "Module-scoped-looking but component-scoped stable refs (useRef Map + useCallback empty-deps) closed over inside a useMemo<ColumnDef>[] cell, to give TanStack Table columns a per-row focus-management escape hatch without breaking referential stability"
    - "Explicit onCloseAutoFocus override on a state-controlled Radix Sheet/Dialog with no <SheetTrigger>, because the primitive's own default handler forecloses its own FocusScope fallback"
key-files:
  created:
    - src/dashboard/src/pages/__tests__/findings-storyline.test.tsx
  modified:
    - src/dashboard/src/pages/findings.tsx
    - .planning/phases/202-finding-storyline-drawer/202-VALIDATION.md
    - quirk/dashboard/static/index.html
    - quirk/dashboard/static/assets/index-82Mpyk0V.css (new hash, replaces index-D0hHYKOp.css)
    - quirk/dashboard/static/assets/index-CjqtsBjf.js (new hash, replaces index-BPKD72MN.js)
decisions:
  - "useMemo<ColumnDef<FindingItem>[]> deps widened from `[]` to `[registerTrigger, openStoryline]` rather than moving the column definition out of the memo — both are useCallback-with-empty-deps values with permanently stable identity, so the array's referential-stability guarantee (D-25/IN-03) is preserved even though the deps array is no longer literally empty. findings-columns-memo.test.tsx only regex-matches the `useMemo<ColumnDef<FindingItem>[]>` type-annotated call-site text, not the deps array contents, so it needed no update and still passes unmodified."
  - "F6 focus-return implemented via an explicit onCloseAutoFocus on SheetContent (the plan's second acceptable option), not solely the plan's first (pre-open .focus() relying on Radix's default previously-focused-element restoration) — see Deviations."
metrics:
  duration: "~1.5h"
  completed: "2026-09-12"
---

# Phase 202 Plan 06: Storyline Trigger, Focus Contract, Extended Sheet Summary

Adds the only keyboard path into the finding-detail Sheet (a per-row `Storyline` trigger button),
extends that Sheet with a rendered `SheetDescription`, a responsive width class list, and an
independently-scrolling body region, mounts `StorylineSections` last in that body, and asserts the
full F1-F9 focus contract with real keyboard/pointer events — fixing a real focus-restoration bug
found along the way.

## What Shipped

### Task 1 — Storyline trigger column, A6 disabled state, focus contract plumbing

- New rightmost `Storyline` column in `findings.tsx`'s memoized `columns` array. Enabled cell:
  `<Button variant="ghost" size="sm" aria-haspopup="dialog" aria-label="Open storyline for {title} at
  {host}:{port}">`. Disabled cell (A6/S7, `finding.id == null`): `disabled`, distinct
  `aria-label="Storyline unavailable for …"`, and the exact `title="Storyline unavailable — this
  finding has no stable identifier in this scan."` attribute — no click handler at all.
- `triggerRefs` (a `useRef<Map<string, HTMLButtonElement>>`), `registerTrigger`, and `openStoryline`
  give every row's trigger button a stable, addressable DOM reference keyed by `row.id` (TanStack's
  default row id = index, stable across a render since `findings` order only changes on filter
  re-derivation, not shuffling).
- The pre-existing row `onClick` (F2, kept as a redundant pointer affordance) and the new trigger's
  `onClick` both call `openStoryline(finding, row.id)`, which focuses that row's trigger button and
  records it in `lastTriggerRef` before calling `setSelectedFinding`.

### Task 2 — Sheet extension

- `style={{ width: 480 }}` replaced with `className="w-full sm:w-[480px] sm:max-w-[480px] flex flex-col"`
  on `SheetContent`.
- `SheetDescription` added inside `SheetHeader`, rendering `{host}:{port} — {protocol}`.
- Body region changed to `flex-1 overflow-y-auto min-h-0`; existing section spacing widened from
  `space-y-3` (12px) to `space-y-4` (16px) — still 4px-grid compliant — so `StorylineSections`, mounted
  last, sits at least 16px from the severity/host badge row per the UI-SPEC's placement rule, without
  a redundant `mt-4` wrapper that would have fought the `space-y` utility's own margin-top rule on the
  same element.
- `StorylineSections` wired to `useFindingStoryline(selectedFinding)` — `data`/`loading`/`error` and
  `retry` as `onRetry`.
- `npm run build` after this task: **zero new warnings** (only the pre-existing, unrelated
  `caniuse-lite` browserslist-staleness advisory that appears on every build in this repo).

### Task 3 — Integration tests, a real focus-restoration bugfix, and rebuilt statics

`src/dashboard/src/pages/__tests__/findings-storyline.test.tsx` — 14 tests, all using real
`userEvent` keyboard/pointer events (no direct handler invocation):

- Column header + one enabled trigger per finding, in the tab order (`aria-haspopup="dialog"`,
  real `<button>`, not disabled).
- A6/S7: disabled trigger has the exact `title` string; clicking it never opens the drawer
  (`queryByRole("dialog")` absent).
- F2: keyboard activation (`{Enter}` on a focused trigger) and mouse row-click both open the drawer,
  `SheetTitle` names the finding (scoped via `within(dialog).getByRole("heading", ...)` to avoid
  ambiguity with the same title text in the table cell behind the overlay).
- F3: `document.activeElement` is inside `SheetContent` with accessible name `Close`.
- F4: 10 consecutive `Tab` presses never move focus outside `SheetContent` — jsdom faithfully
  exercises Radix's real `FocusScope` trap here, so **no jsdom limitation needed to be named for F4**.
- F5+F6 (Escape), F6 via the Close button, F6 via an overlay click (found via
  `document.querySelector(".fixed.inset-0.z-50")`, the overlay's own class list), and F6 after a
  mouse-initiated open — all four assert
  `document.activeElement?.getAttribute('aria-label') === 'Open storyline for {title} at {host}:{port}'`.
  One assertion example (Escape path):
  ```ts
  await user.keyboard("{Escape}")
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  expect(document.activeElement?.getAttribute("aria-label")).toBe(triggerLabel(FINDING_A))
  ```
- Cross-finding leakage: open A (narrative "Finding A's narrative text."), close mid-fetch
  (mocked hook set to `loading: true, data: null`), open B (narrative "Finding B's narrative
  text.") — asserts B's narrative renders and A's narrative string is absent anywhere in the
  document.
- S6: `narrative: null` with populated `theme_*` fields — asserts the A5 absence string renders
  AND `Score-lift attribution` / theme title / `+4` all render in the same pass (composition-level
  proof, not the isolated component).
- S8: mocked hook error state — error string + `Retry storyline` render, A5 absence string does
  not.
- No-console-output: `console.warn`/`console.error` spies assert zero calls across an open+close
  cycle — the same condition 202-07's a11y harness gate enforces.

**No jsdom limitation needed naming for F4 or F7** — both asserted faithfully against Radix's real
implementation (`FocusScope`'s trap, and the overlay's real DOM element via its class selector).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Radix's default `onCloseAutoFocus` forecloses its own focus-restoration
fallback on a `<SheetTrigger>`-less Sheet**

- **Found during:** Task 3, writing the F5/F6 RED tests (they failed with
  `document.activeElement` = `null`/`<body>` instead of the triggering button).
- **Root cause:** `@radix-ui/react-dialog`'s `DialogContentModal` always supplies its own
  `onCloseAutoFocus`: `(event) => { event.preventDefault(); context.triggerRef.current?.focus() }`.
  Since `findings.tsx`'s `Sheet` is state-controlled with no `<SheetTrigger>` (by design — D-03,
  and the UI-SPEC's own F2 note anticipated this), `context.triggerRef.current` is always `null`,
  so that default handler does nothing useful **but still calls `event.preventDefault()`
  unconditionally** — which makes `@radix-ui/react-focus-scope`'s own fallback
  (`focus(previouslyFocusedElement ?? document.body)`) unreachable, since that fallback is itself
  gated on `!event.defaultPrevented`. The pre-open `trigger.focus()` call from Task 1 (F2/F6's
  first suggested implementation) was therefore necessary but not sufficient: it correctly primed
  `previouslyFocusedElement`, but Radix's own default handler discarded that opportunity on every
  close, silently dropping focus to `<body>`.
- **Fix:** implemented the UI-SPEC's explicitly-permitted alternative — "capture its ref and
  restore explicitly in `onCloseAutoFocus`." Added `lastTriggerRef` (set on every open alongside
  the pre-open `.focus()` call, which is now belt-and-braces rather than load-bearing) and passed
  an explicit `onCloseAutoFocus={(e) => { e.preventDefault(); lastTriggerRef.current?.focus() }}`
  to `SheetContent`. Because Radix's `composeEventHandlers` runs the caller-supplied handler
  first and skips its own default once `event.defaultPrevented` is true, this handler now wins.
- **Files modified:** `src/dashboard/src/pages/findings.tsx`.
- **Commit:** `2039d8f2` (bundled with the Task 3 test-file/statics commit, since it was found and
  fixed while writing that task's RED tests, before GREEN).

### Minor, in-scope adjustments (not deviations from a `must_haves` truth)

- Widened `space-y-3` → `space-y-4` on the Sheet's body wrapper (12px → 16px, both 4px-grid
  values) to satisfy the UI-SPEC's "separated by at least 16px" placement rule for
  `StorylineSections` without stacking a conflicting `mt-4` on the same element. Recorded here per
  CLAUDE.md's "keep diffs minimal" spirit, since it slightly changes the existing
  Description/Remediation/Quantum-Context section spacing, not just the new section's.

## Self-Check: PASSED

- FOUND: src/dashboard/src/pages/findings.tsx
- FOUND: src/dashboard/src/pages/__tests__/findings-storyline.test.tsx
- FOUND: .planning/phases/202-finding-storyline-drawer/202-06-SUMMARY.md
- FOUND: quirk/dashboard/static/index.html
- FOUND: quirk/dashboard/static/assets/index-82Mpyk0V.css
- FOUND: quirk/dashboard/static/assets/index-CjqtsBjf.js
- FOUND commit: d1e50337 (Task 1)
- FOUND commit: f1dab494 (Task 2)
- FOUND commit: 2039d8f2 (Task 3)

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired data paths were introduced.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary changes. The trigger's `aria-label`/
`title` carry only the finding's own title/host/port, already visible in the row (T-202-27,
pre-dispositioned `accept` in the plan's threat model).
