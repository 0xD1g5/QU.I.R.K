# Tailwind theme-class shorthand badges remain guard-blind outside FIX-04's scope

**Filed:** 2026-09-30 (Phase 218 plan 218-04, D-07/D-08 TODO-220 ledger)
**Priority:** P3 — no known failing pair confirmed; this is an instrument-coverage gap, not a
confirmed defect
**Owner:** 999.118 (HORIZON.md ledger row; backlog .planning/backlog/999.118-a11y-design-calls-and-instrument-blind-spots/).
**Re-pointed:** 2026-10-01 by Phase 221 (INT-01). The previous owner phase closed without picking this up.
**Status:** open, not triaged

## What happens

`badge-contrast-guard.test.ts`'s `BG_TOKEN_RE` (`bg-\[hsl(var(--…\)\)\]`) and
`badge-contrast-evaluator.ts` only see arbitrary-value background classes
(`bg-[hsl(var(--x))]`). Any badge using plain Tailwind theme-class shorthand
(`bg-destructive`, `bg-quantum-safe/N`, `bg-primary`, etc.) is structurally invisible to
RATCHET-01, regardless of whether its actual contrast passes or fails.

218-CANDIDATES.md's "Guard-blind triage" table enumerated every shorthand hit found by
`grep -rnE "bg-(destructive|quantum-safe|primary|secondary)(/[0-9]+)?\b"` this phase and
triaged each: the two D-01/D-02-repaired sites (shadcn destructive variant, quantum-safe
maturity/risk badges) are now individually guarded (see
`shadcn-destructive-variant-contrast-guard.test.ts`,
`quantum-safe-text-badge-contrast-guard.test.ts`). **Left un-guarded and un-measured**, because
no FIX-04 candidate touches their tokens:

- `lib/qramm-constants.ts:39-41` — `MATURITY_BADGE_CLASS[3]` (`severity-low`), `[2]`
  (`quantum-at-risk`), `[1]` (`quantum-vulnerable`) — same shorthand shape as the `[4]` entry
  this phase fixed, different tokens, never measured.
- `components/ui/progress.tsx`, `tooltip.tsx`, `switch.tsx`, `checkbox.tsx`, `skeleton.tsx` —
  `bg-primary(/N)` non-destructive, non-quantum-safe utility chrome (explicitly out of FIX-04's
  token scope, per UI-SPEC's "Accent … unchanged this phase").

## Why it is P3

No ratio has been measured for any of these — they may already pass AA. This is a coverage gap
(the instrument can't see the class), not a confirmed contrast failure. Promote to a real defect
only after measuring.

## Suggested first step

Extend `badge-contrast-evaluator.ts` (or a sibling extraction module) to recognize Tailwind
theme-class shorthand (`bg-<token>(/N)?` where `<token>` resolves via `tailwind.config.ts`'s
`theme.extend.colors` map, not just the arbitrary-value `bg-[hsl(var(--x))]` construct) — this
closes the blind spot structurally instead of requiring a hand-written guard per site, which is
the failure mode this project's CLAUDE.md repeatedly warns about ("a hand-maintained list drifts
from the real set"). Re-run against the full `src/` tree once built; triage any new failing pair
the same way 218-CANDIDATES.md did.
