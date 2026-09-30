# `--status-critical` bare text span fails AA in dark theme (certificates)

**Filed:** 2026-09-30, from Phase 218 plan 218-05 (CI-only axe baseline round-trip, D-09 residual
triage).
**Priority:** P3 — axe-confirmed live violation (~4.0:1 dark, corroborating hand calculation
against `--card`; below the 4.5:1 AA-normal-text floor).
**Owner:** Phase 220 (CI Instrument Truth).
**Status:** open, not triaged.

## What happens

`/certificates`, dark theme (also the `empty` and `loading` fixture variants of the same route): a
bare `<span class="text-sm text-[hsl(var(--status-critical))] flex items-center gap-1">` text
span, no badge background. `--status-critical` (dark `:root`) is `0 72% 51%` (`#dc2828`); against
the dark `--card`/`--ds-bg-base` (`#0d0f14`) it measures ~4.0:1, below AA-normal-text's 4.5:1.
Axe-confirmed as a live violation across three fixture variants (default, empty, loading) in the
218-05 CI round-trip (run 36776265139) and every prior round-trip back through at least 217-04.

Note: `pages/certificates.tsx`'s OTHER `--status-critical` consumer (a badge pair, drained by
Phase 217's FIX-01) is unrelated and already fixed — this is a second, bare-text use of the same
token, not a residual of that fix.

## Why it is not a Phase 218 fix

Not one of FIX-04's 3 named design-call tokens (`--destructive`, `--quantum-safe`,
`--badge-modbus`); RATCHET-01's badge baseline is `{}` as of 218-04, and this is a bare text span
with no background pair, so it is not a FIX-05 failure under REQUIREMENTS.md's literal definition.

## Suggested first step

Either mint a `--status-critical-foreground`-style darker/lighter dark-theme variant for text-only
uses (parallel to FIX-03's `-foreground` token pattern), or move this specific span to
`--destructive` (now dark-theme AA-safe at 5.50:1 per 218-04's D-01) if the two convey the same
severity meaning. Bring to an operator checkpoint if the colour itself needs to change.
