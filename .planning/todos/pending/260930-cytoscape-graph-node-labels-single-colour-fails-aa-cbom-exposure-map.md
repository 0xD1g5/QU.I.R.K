# CBOM and exposure-map Cytoscape graphs paint one `--chart-node-label` colour on every node fill

**Filed:** 2026-09-30, from the Phase 218-03 operator checkpoint.
**Priority:** P2. This is probably a live AA failure on canvas text, and every contrast instrument is blind to it.
**Owner:** Phase 220 (CI Instrument Truth). The instrument side is the canvas blind spot.

## Evidence

The operator flagged the **roadmap** graph as "rough in light mode" (screenshot, 218-03 Round 1).
Measured: one label colour per theme (`--chart-node-label`, `index.css:131` white dark / `:239`
`#11141c` light) on NOW/NEXT/LATER fills. NOW light 2.65, NEXT light 3.78, NEXT dark 2.14 and LATER
dark 2.30 all fail. The roadmap graph was fixed in Phase 218 (D-07(3): per-phase label colour).

`cbom.tsx` and `exposure-map.tsx` resolve the **same** `--chart-node-label` for their node labels
(see the comment at `index.css:131`: "cbom/exposure-map/roadmap"). Their fills were **not
measured**. Re-derive every fill × theme × label pair before fixing.

## Why nothing catches it

Cytoscape draws to `<canvas>`. axe sees no text nodes, and `badge-contrast-guard` only reads
`bg-[hsl(var(--x))]` class strings.
