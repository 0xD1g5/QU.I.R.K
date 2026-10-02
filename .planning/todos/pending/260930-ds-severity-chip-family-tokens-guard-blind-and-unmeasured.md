# The `.severity-*-chip` / `--ds-*` design-token chip family is contrast-unguarded and axe-flagged in light theme

**Filed:** 2026-09-30, from Phase 218 plan 218-05 (CI-only axe baseline round-trip, D-09 residual
triage).
**Priority:** P3 — one confirmed axe violation in this family so far (qramm-assessment,
`severity-accent-chip`); the sibling classes/tokens are unmeasured.
**Owner:** 999.118 (HORIZON.md ledger row; backlog .planning/backlog/999.118-a11y-design-calls-and-instrument-blind-spots/).
**Re-pointed:** 2026-10-01 by Phase 221 (INT-01). The previous owner phase closed without picking this up.
**Status:** open, not triaged.

## What happens

`src/dashboard/src/index.css` defines a `.severity-{critical,high,ok,medium,accent}-chip` family
(around line 297-320), each pairing a `--ds-<name>` text colour with a `--ds-<name>-dim`
background and `--ds-<name>-bdr` border — e.g. `.severity-accent-chip { background:
var(--ds-accent-dim); color: var(--ds-accent); }`. This is neither the Tailwind arbitrary-value
`bg-[hsl(var(--x))]` shape `badge-contrast-evaluator.ts`'s `BG_TOKEN_RE` matches, nor the Tailwind
theme-class shorthand (`bg-destructive`, `bg-quantum-safe/N`) the sibling todo
(`260930-tailwind-shorthand-badge-sweep-remaining-guard-blind-sites.md`) tracks — it is a
hand-authored CSS class consuming raw CSS custom properties, invisible to RATCHET-01 by a third
mechanism.

Confirmed live in the 218-05 CI axe round-trip (run 36776265139): `/qramm-assessment`, light
theme — the `severity-accent-chip` class on the "Auto-filled from scan" `Badge`
(`components/qramm/QuestionCard.tsx:91-97`, `role="status"`) is an axe color-contrast violation.

A related but distinct site in the same `--ds-*` token family: `/findings` (storyline fixture),
light theme — `<span style="color: var(--ds-ok)">+7</span>` delta indicator
(`FindingStorylineSections.tsx` or its data source), an inline reference to `--ds-ok` rather than
the `.severity-ok-chip` class, but drawing from the same token block and carrying the same
instrument-blind-spot shape. Folded into this todo rather than filed separately since both are
`--ds-*` design-token contrast debt with no dedicated guard.

## Why it is not a Phase 218 fix

Neither site uses one of FIX-04's 3 named tokens (`--destructive`, `--quantum-safe`,
`--badge-modbus`), and RATCHET-01's badge baseline (`badge-contrast-baseline.json`) is `{}` as of
218-04 — these are non-RATCHET-01 chip/text pairs, not badge pairs, so they are not FIX-05
failures per REQUIREMENTS.md's literal definition.

## Suggested first step

Measure every `--ds-*` chip pair (`severity-critical`, `severity-high`, `severity-ok`,
`severity-medium`, `severity-accent`) in both themes with the project's own
`color-contrast-helpers.ts`, the same way 218-CANDIDATES.md's collateral tables did for
`--quantum-safe`. Any failing pair gets a design-call-style operator review (same shape as
FIX-04); a general guard could then assert the whole family the way
`muted-token-contrast-guard.test.ts` does for `--ds-text-muted`.

## Phase 221 note (2026-10-01)

Measured by `src/dashboard/src/components/__tests__/ds-severity-chip-contrast-guard.test.ts`; failing
pairs ratcheted, not fixed (they need an operator design call). Ratios in 999.118. Stays pending.
