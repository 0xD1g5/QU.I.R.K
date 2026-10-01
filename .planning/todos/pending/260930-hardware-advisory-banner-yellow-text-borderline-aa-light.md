# Hardware advisory-banner text (Tailwind `yellow-700`/`dark:yellow-300`) is an axe-confirmed light-theme contrast violation

**Filed:** 2026-09-30, from Phase 218 plan 218-05 (CI-only axe baseline round-trip, D-09 residual
triage).
**Priority:** P3 — axe-confirmed live violation; hand-calculated ratio is borderline (~4.6-4.9:1
against an approximated tinted background) and needs a precise re-measurement, not a guess.
**Owner:** 999.118 (HORIZON.md ledger row; backlog .planning/backlog/999.118-a11y-design-calls-and-instrument-blind-spots/).
**Re-pointed:** 2026-10-01 by Phase 221 (INT-01). The previous owner phase closed without picking this up.
**Status:** open, not triaged.

## What happens

`/hardware`, light theme: two `role="note"` advisory banners
(`<div class="rounded-md border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm
text-yellow-700 dark:text-yellow-300">`) — "Hardware findings are advisory-only and do not affect
the readiness score." and "Based on SNMP-derived network-path evidence; not independently
confirmed by traffic inspection." — are flagged by axe as `color-contrast` violations in the
218-05 CI round-trip (run 36776265139).

This is plain Tailwind default-palette text (`text-yellow-700`) on a Tailwind alpha-tinted
background (`bg-yellow-500/10`), not one of FIX-04's 3 named design-call tokens and not a
RATCHET-01 badge pair (no `bg-[hsl(var(--x))]` background). A 2026-09-30 hand calculation against
an approximated `bg-yellow-500/10`-over-card background put the ratio around 4.6-4.9:1 —
borderline, and imprecise because the approximation didn't sample the actual rendered card
background. Axe's own live measurement is the authoritative one; this todo exists to get a
precise re-measurement, not to guess further.

## Why it is not a Phase 218 fix

Not one of FIX-04's named tokens; RATCHET-01's badge baseline is `{}` as of 218-04, and this is a
banner text/background pair, not a badge pair, so it is not a FIX-05 failure under
REQUIREMENTS.md's literal definition.

## Suggested first step

Re-measure precisely with the project's `color-contrast-helpers.ts` against the actual rendered
`--card`/`bg-yellow-500/10` composite in both themes (dark uses `dark:text-yellow-300`, unmeasured
here — axe did not flag it, but re-derive rather than assume it passes). If it fails, this is
either a design call (bring to an operator checkpoint) or a mechanical Tailwind-shade bump.
