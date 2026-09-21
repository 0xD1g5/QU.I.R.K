---
type: todo
created: 2026-09-21
source: phase-206 plan 12 (COV-04); the UAT-7-21 FAIL verdict produced by plan 206-11's audit
priority: medium
requirement: none (UAT-7-21 disposition input, not itself a requirement)
resolves_phase: null
---

# 50 hardcoded colour literals across 8 dashboard pages bypass the theme tokens (UAT-7-21 FAILS)

`docs/UAT-SERIES.md`'s UAT-7-21 ("Dashboard Theme — No Hardcoded Colors") requires the major
dashboard components to draw their colours from the design-system tokens rather than from `#hex`
or raw `hsl(N N% N%)` literals. **They do not.** Plan 206-11 built a full-strength source audit for
this case — no allowlist, no baseline snapshot, no narrowed pattern, assertion
`expect(violations).toEqual([])` — and it genuinely fails.

The audit node is `src/dashboard/src/components/__tests__/hardcoded-color-audit.test.tsx::"finds no
hardcoded hex or raw hsl color literals in the major dashboard page and shell components"`. It is
deliberately marked `it.fails`, so it reports **green while the debt exists** and goes **red with
`Error: Expect test to fail` the day the product is fixed** — that red is the signal to drop
`.fails` and re-disposition UAT-7-21 to PASS. A hard-red node would have taken
`dashboard-quality.yml` and the UAT citation guard's vitest execution leg down with it, hiding the
finding rather than publishing it.

## The inventory, re-derived independently on 2026-09-21

Counted by plan 206-12 with a **standalone scanner written for the purpose**, not by reading the
audit's own output — per this project's standing rule that a component's own extractor must not be
the only thing that measures the component. The scanner re-implements the same file set
(`readdirSync(src/pages/*.tsx)` plus `components/sidebar.tsx`), the same comment-stripping, and the
same two patterns, and it independently reproduced the audit's headline:

```
$ node /tmp/recount.mjs src/dashboard/src
audited files: 27
TOTAL violations: 95
  45 pages/print.tsx
  12 pages/trends.tsx
  11 pages/cbom.tsx
   9 pages/executive.tsx
   6 pages/exposure-map.tsx
   4 pages/healthcare.tsx
   3 pages/roadmap.tsx
   3 pages/sensors.tsx
   2 pages/schedules.tsx
NON-print total: 50 across 8 files
```

`components/sidebar.tsx` is **clean** — its only `#hex` text sits inside a line comment, which the
detector strips.

**`pages/print.tsx`'s 45 are reported separately and are arguably by design.** `/print` is a
white-background, theme-independent client deliverable; its injected `PRINT_CSS` is supposed to be
independent of the dark dashboard palette. That is a classification of the finding, not a narrowing
of the detector — the audit reports all 95.

**The honest remediation headline is therefore 50 literals across 8 dashboard page files.**

### Per-site inventory (the 50, excluding `print.tsx`)

| File | Lines |
|---|---|
| `pages/trends.tsx` (12) | 23, 24, 25, 26, 27, 28, 196, 197, 198, 199, 200, 201 — Recharts series colours, raw `hsl(N N% N%)` triples, declared twice (a constant block and an inline repeat) |
| `pages/cbom.tsx` (11) | 39, 40, 41, 278, 310, 327, 336, 343, 350, 358, 436 — Cytoscape node/edge stylesheet literals plus one legend swatch |
| `pages/executive.tsx` (9) | 32, 38, 39, 40, 143 (×3), 545, 692 — severity palette, `bg-[#d4893a]` Tailwind arbitrary values, one inline `style={{ color: "#d4893a" }}` |
| `pages/exposure-map.tsx` (6) | 148, 149, 165, 166, 167, 190 — `cssVar(...) \|\| "#hex"` fallbacks and a Cytoscape literal |
| `pages/healthcare.tsx` (4) | 134, 150, 204 (×2) — inline `style={{ color: … }}` on icons |
| `pages/roadmap.tsx` (3) | 163, 296, 305 — badge/stylesheet literals |
| `pages/sensors.tsx` (3) | 46 (×3) — `bg-[#d4893a]` / `text-[#d4893a]` arbitrary values |
| `pages/schedules.tsx` (2) | 193 (×2) — `border-[#2b8a86]` / `text-[#2b8a86]` arbitrary values |

### The verdict survives the narrowest possible reading of the case

UAT-7-21's criterion 2 is specifically about **inline styles**. Even under that narrowest reading
the case still fails, on four sites — derived by an independent grep, not carried forward:

```
$ grep -nE 'style=\{\{[^}]*#[0-9a-fA-F]{3,6}' src/dashboard/src/pages/*.tsx src/dashboard/src/components/sidebar.tsx
pages/executive.tsx:545:  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" style={{ color: "#d4893a" }} aria-hidden="true" />
pages/healthcare.tsx:134: <HeartPulse className="h-6 w-6 mt-0.5 flex-shrink-0" style={{ color: "#4ba8a8" }} aria-hidden="true" />
pages/healthcare.tsx:150: <ShieldCheck className="h-4 w-4" style={{ color: "#4ba8a8" }} aria-hidden="true" />
pages/healthcare.tsx:204: <p className="text-xs flex items-center gap-1.5" style={{ color: risk === "high" ? "#e05555" : "#d4893a" }}>
```

## Why this matters beyond a UAT box

These literals are **dark-theme values baked into the component**. The theme toggle (UAT-7-22)
switches a single class on `<html>`; anything painted from a literal does not follow it. The four
inline-style sites above are the sharpest case — an icon hardcoded to `#4ba8a8` renders identically
in both themes regardless of what the light palette says. `exposure-map.tsx`'s
`cssVar(...) || "#hex"` fallbacks are the mildest: the token is tried first, and the literal is only
a degraded path.

## What a real fix would look like

1. **The two Cytoscape stylesheets (`cbom.tsx`, `roadmap.tsx`, `exposure-map.tsx`) are the
   structural half.** Cytoscape cannot read a CSS custom property, which is why these literals
   exist. The fix is to resolve tokens to concrete values at render time — `exposure-map.tsx`'s
   `cssVar()` helper is already the right shape and should be lifted to a shared module and used by
   all three, with the `|| "#hex"` fallbacks dropped once the tokens are guaranteed present.
2. **`trends.tsx`'s 12 are a duplication bug as much as a theming one** — the same six series
   colours are declared at lines 23-28 and repeated at 196-201. Collapse to one token-derived
   constant.
3. **The Tailwind arbitrary values (`bg-[#d4893a]`, `text-[#2b8a86]`, `border-[#2b8a86]`) should
   become named theme tokens** in the Tailwind config, so `sensors.tsx`, `schedules.tsx` and
   `executive.tsx` share one definition.
4. **The four inline `style={{ color: … }}` sites become token classes** — the smallest and highest
   value change, since they are the ones that ignore the theme outright.
5. **Leave `print.tsx` alone, or move its 45 behind an explicit, documented print-palette constant**
   so the audit can classify them rather than report them as accidental.

## Feasibility & Effort

**Grade: CONFIRMED.** The count, the per-site list and the inline-style subset were each
re-derived by command on 2026-09-21; none is carried forward from prose.

- *95 violations exist, 50 outside `print.tsx`* — CONFIRMED by an independent scanner reproducing
  the audit's number from the same file set (output pasted above).
- *A token-resolution helper already exists in-repo* — CONFIRMED: `cssVar(...)` at
  `src/dashboard/src/pages/exposure-map.tsx:148-149`, used exactly for this purpose.
- *The audit will detect the fix without being edited* — CONFIRMED: the audited file set is
  `readdirSync`-derived at run time, and 206-11 proved sensitivity by injecting one literal and
  watching the reported set move 95 → 96 naming the exact new site.
- *`sidebar.tsx` is already clean* — CONFIRMED: 0 violations.

**Size: M.** Not S: item 1 is a real refactor across three Cytoscape call sites, and the Tailwind
token additions touch the shared config. Not L: there is no API, schema, or behavioural change, the
per-site list is fully enumerated above, and the audit node gives a precise pass/fail oracle for
each step.

**Open unknowns:**
- Whether every literal has a token equivalent in the current Tailwind/CSS-variable palette, or
  whether the fix must *add* tokens (`#d4893a`, `#4ba8a8`, `#2b8a86`, `#e05555` all look like
  palette members that were never promoted). Enumerate against the theme config before starting —
  do not assume a 1:1 mapping exists.
- Whether `print.tsx`'s 45 should be exempted structurally (a separate audited-set carve-out, which
  would weaken the detector) or re-expressed as a named print palette (which would not). Item 5
  recommends the latter; the decision is not made here.
- Whether any of `cbom.tsx`'s Cytoscape literals are load-bearing for the quantum-safety
  green/amber/red correspondence that UAT-7-27 names as uncovered. If so, fixing them should be
  sequenced with that case rather than ahead of it.

**Spike needed: NO** for items 2-4 (mechanical, with an oracle). **YES, a short one, for item 1** —
confirm that resolving a CSS custom property to a concrete value at Cytoscape-init time actually
survives a theme switch (the graph is initialised once; a token resolved at init will not re-resolve
when the theme changes unless the component re-initialises). That is a real behavioural question the
source cannot answer by inspection, and getting it wrong would trade a static-colour bug for a
stale-colour bug.

## Acceptance (for whoever picks this up)

- The audit node runs **red** with `Error: Expect test to fail`, and `.fails` is then removed so it
  is a standing green guard.
- `print.tsx`'s treatment is explicit — either fixed, or carried as a named, documented print
  palette the audit reports as a distinct category.
- UAT-7-21 is re-dispositioned from FAIL to PASS in `docs/UAT-SERIES.md`, citing the same node.
