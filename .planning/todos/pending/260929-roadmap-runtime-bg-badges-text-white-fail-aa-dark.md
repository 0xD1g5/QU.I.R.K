# `roadmap.tsx` detail-panel badges pair static `text-white` with a runtime `--status-warning` background — 2.13:1 in dark theme

**Filed:** 2026-09-29, from Phase 217 (spike `217-SPIKE.md` § case (a); re-confirmed by `217-UI-REVIEW.md`).
**Priority:** P1 — a real, currently-shipping WCAG AA failure that every contrast instrument is blind to.
**Owner:** Phase 218 (its FIX-05 closing assertion says "anywhere"); instrument side is Phase 220.

## The defect

- `src/dashboard/src/pages/roadmap.tsx:345` — `<Badge className="text-xs text-white" style={{ background: PHASE_COLORS[selected.phase] ?? … }}>`.
  `PHASE_COLORS["NEXT"]` resolves to `hsl(var(--status-warning))`.
- `roadmap.tsx:353-354` — same shape via `CLOSURE_STATE_COLOR`; `CLOSURE_STATE_TOKEN.resurfaced = "--status-warning"`.

White on dark `--status-warning` (`38 92% 50%`, `#f59f0a`) = **2.13:1 — FAILS AA**. Light theme
(`#9d6607`) = 4.84:1, passes. Dark-theme-only failure.

## Why nothing catches it

`badge-contrast-guard` extracts literal `bg-[hsl(var(--x))] text-y` pairs from source; a background
set through `style={{ background: MAP[key] }}` is invisible to it. The axe `/roadmap` sweep only
sees the panel if an item with `phase === "NEXT"` or `closure_state === "resurfaced"` is *selected*,
which the fixture sweep does not do.

## Likely fix

Use `--status-warning-foreground` (minted in Phase 217: dark black / light white) for the text when
the background is `--status-warning` — i.e. derive the text colour from the same map key rather
than a static `text-white`. Verify by mutation, per project convention.
