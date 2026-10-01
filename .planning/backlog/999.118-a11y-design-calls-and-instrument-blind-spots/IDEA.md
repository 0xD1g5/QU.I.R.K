# 999.118 — Dashboard a11y design calls and instrument blind spots carried out of v5.26

**Filed:** 2026-10-01 (Phase 221, gap closure of v5.26-MILESTONE-AUDIT INT-01)
**Priority:** P2 — measured WCAG 1.4.3 failures and unmeasured surfaces that Phase 218 handed to Phase 220, which closed without picking them up.
**Operator decision:** successor to 999.117. Colour changes here require an operator design call (FIX-04 shape); they are never made unilaterally by an executor.
**Horizon entry:** `HORIZON.md` Open-Item Ledger, row `999.118`.

## Why this exists

Ten todos under `.planning/todos/pending/` named Phase 220 (CI Instrument Truth) as owner. Phase 220 closed
(PR #47/#48) and delivered CITRUTH-01/02/03 only. Every hand-off was therefore ownerless, and the one place
a future session looks (HORIZON.md) had no row. This item is that row's detail. `**Owner:** 999.118` on each
todo points here; provenance is kept on a `**Re-pointed:**` line.

## Scope (measured; hand-calculated figures are labelled)

Measured by Phase 221 plan 221-02 (token pairs resolved from `src/dashboard/src/index.css`, WCAG 2.1 luminance):

### DS severity chips (`.severity-*-chip`, text vs `--ds-*-dim` tint blended over surface) — todo `260930-ds-severity-chip-family-tokens-guard-blind-and-unmeasured.md`

| Key | Ratio |
|---|---|
| dark\|critical\|surface | 4.23 |
| light\|critical\|surface | 4.08 |
| light\|accent\|base | 3.15 |
| light\|accent\|surface | 2.86 |
| light\|high\|base | 3.78 |
| light\|high\|surface | 3.42 |
| light\|medium\|base | 4.27 |
| light\|medium\|surface | 3.88 |
| light\|ok\|base | 3.88 |
| light\|ok\|surface | 3.54 |

10 of 20 pairs fail; baseline `ds-chip-contrast-baseline.json`. Light theme inherits the dark rgba `-dim` tints.

### Cytoscape node labels (`--chart-node-label` vs fill) — todo `260930-cytoscape-graph-node-labels-single-colour-fails-aa-cbom-exposure-map.md`

| Key | Ratio |
|---|---|
| cbom\|Safe\|dark | 2.30 |
| cbom\|At Risk\|dark | 2.13 |
| cbom\|At Risk\|light | 3.80 |
| cbom\|Vulnerable\|light | 2.64 |
| cbom\|Unknown\|light | 2.38 |
| cbom\|system\|light | 1.25 (CBOM system node, see row below) |
| exposure-map\|node\|dark | 3.14 |
| exposure-map\|node\|light | 3.98 |

8 failing entries; baseline `cytoscape-label-contrast-baseline.json`.

### Other re-pointed todos

| Todo | Measured / stated | Theme |
|---|---|---|
| `260930-lifecycle-advisory-firewall-hues-fail-aa-in-light-theme.md` | ~2.9:1 / ~3.9:1 (hand calculation, axe-confirmed failure) | light |
| `260930-text-primary-nav-link-fails-aa-light-root.md` | ~3.5:1 (hand calculation, axe-confirmed) | light |
| `260930-status-critical-bare-text-span-fails-aa-dark-certificates.md` | ~4.0:1 (hand calculation, axe-confirmed) | dark |
| `260930-hardware-advisory-banner-yellow-text-borderline-aa-light.md` | ~4.6-4.9:1 approximated, needs precise re-measurement (figure from its todo) | light |
| `260930-tailwind-shorthand-badge-sweep-remaining-guard-blind-sites.md` | evaluator extension for `bg-destructive`/`bg-primary` shorthand; a named exclusion in `UNMEASURED-EXCLUSIONS.md` (written by 221-06) | both |
| `260929-canonical-demo-db-lacks-rows-for-uat-217-visual-legs.md` | fixture rows (30-89-day cert, `--chart-tls` badge row); P3 | n/a |
| `260929-a11y-empty-loading-variant-legs-are-near-vacuous.md` | fixed in Phase 221 (221-03/05); Owner re-pointed so nothing is ownerless meanwhile | n/a |
| `260929-a11y-axe-harness-does-not-cover-scan-history-sensors-and-more.md` | fixed in Phase 221 (221-06/08) where it holds; remaining un-swept pages are listed in `UNMEASURED-EXCLUSIONS.md` | n/a |
| Rendered cytoscape canvas text | exclusion: no instrument reads canvas pixels | both |
| CBOM `system` node, light theme | 1.25:1 (cbom|system|light, 221-02); rendered defect, operator-confirmed 2026-10-01 ("no I cannot read their labels") | light |

## Feasibility & Effort

**Overall: LIKELY / M-L, operator-gated** — checks run 2026-10-01.

| Item | Feasibility | Size | Unknowns | Spike? |
|---|---|---|---|---|
| DS chip light-theme tints | **CONFIRMED** — light block `src/dashboard/src/index.css:195-202` defines `--ds-*` text colours; the `-dim` tints are not redefined there so light inherits the dark rgba, which is the root of the 10 failures; guard is `ds-severity-chip-contrast-guard.test.ts` | S-M, operator-gated (design call) | Whether light needs its own opaque `-dim` tints or darker text | no |
| Cytoscape per-fill label colour | **CONFIRMED** — one `--chart-node-label` per theme (`src/dashboard/src/index.css:133` dark, `:243` light); roadmap graph already uses a per-phase label colour (Phase 218 D-07(3)); `cbom.tsx:60` `QS_TOKEN` drives fills | M | exposure-map has two node classes; CA hub passes at 16-18:1 | no |
| CBOM system node light label | **CONFIRMED token-level** — `cbom.tsx:307-312` sets `background-color: slateDark` and `color: slateLight`; light block `index.css:238,240` makes slate-dark 24% and slate-light 30% lightness (the "role reverses" comment) | S | Whether it renders as described (operator look) | no |
| Lifecycle advisory hues | **LIKELY** — hues are pinned by `lifecycle-advisory-guard.test.ts:14` `FORBIDDEN_PALETTE` (and `vendor-trend-advisory-guard.test.ts`); fixing means editing the guard's literals too | S-M, operator-gated | Whether the guard's purpose (keep hues distinct from severity) survives a darker teal/magenta | no |
| `text-primary` link, `status-critical` span, hardware banner | **LIKELY** — each is a single site; `--primary` is also the focus-ring colour so a global change has wider blast radius than the site count | S each | Hardware banner needs a precise blend measurement | small |
| Tailwind-shorthand evaluator extension | **LIKELY** — `badge-contrast-evaluator.ts:67` `BG_TOKEN_RE` matches only `bg-[hsl(var(--x))]`; shorthand needs a Tailwind-theme-to-token map | M | Opacity-suffixed classes (`bg-quantum-safe/N`) need blending | YES, small |
| Canonical demo DB rows | **CONFIRMED** — pure fixture/seed data | S | none | no |
| Rendered canvas text | **UNKNOWN** — would need pixel sampling or a Cytoscape render hook | L | Whether headless Chromium canvas text is deterministic enough to gate | YES |

### Sequencing

Operator design calls first (DS chip tints, per-fill cytoscape labels, lifecycle hues), each behind human
visual review as 213-09 and 218-03 were. Then the single-site fixes. The evaluator extension and the canvas
spike are independent and can run any time; the ratchets from 221-02 turn each fix into a shrink-only number.

### Costs not visible in the site count

- Every `.tsx`/`.css` edit needs `npm run build`; `quirk/dashboard/static` is committed.
- `--primary` doubles as the focus-ring colour; changing it moves keyboard-focus visibility.
- Lifecycle hues are guarded by `FORBIDDEN_PALETTE`; the guard must be edited in the same change.
- New tokens need `:root` and `.light` parity (`theme-token-vocabulary.test.ts`).
- Fixing a failing key must shrink the matching baseline JSON in the same change (the ratchet fails in the improvement direction until it does).
