/**
 * Roadmap Cytoscape graph node-label contrast guard — Phase 218 plan 218-04
 * (D-07(3), operator scope addition approved at the 218-03 checkpoint).
 *
 * WHAT THIS PROTECTS. `roadmap.tsx`'s `buildRoadmapStyle()` used to paint
 * EVERY node's label text with one shared `--chart-node-label` colour
 * (white dark / `#11141c` light) regardless of which phase fill the node
 * sat on. Measured pre-fix: NOW light 2.65 FAIL, NEXT light 3.78 FAIL, NEXT
 * dark 2.14 FAIL, LATER dark 2.30 FAIL — 4 of 6 (phase, theme) pairs failed
 * AA. The graph renders to a `<canvas>`, so neither axe nor
 * `badge-contrast-guard.test.ts` (which only ever sees real-DOM `bg-[ ... ]`
 * classes) can see this site at all — it is a genuine blind spot both
 * instruments share, not an oversight either one could have caught.
 *
 * THE FIX. `buildRoadmapStyle()` now sets a per-phase `color` on each
 * `node[phase='…']` selector, resolved from the SAME `PHASE_FG_TOKEN` map
 * the real-DOM detail-panel badge (`PHASE_FG`) derives from — see
 * `roadmap-badge-foreground-guard.test.ts`'s own module docstring for that
 * half. This guard tests the CANVAS half: that each phase's resolved label
 * colour actually clears AA against that SAME phase's own fill, in both
 * themes, and that `buildRoadmapStyle()`'s source actually wires a per-phase
 * "color" into each `node[phase='…']` selector rather than falling back to
 * the shared base colour (the exact regression a revert would reintroduce).
 *
 * SCOPE IS DERIVED AT RUN TIME. `PHASE_TOKEN` and `PHASE_FG_TOKEN` are
 * parsed straight out of `roadmap.tsx` on every run, and every colour is
 * resolved from `index.css` on every run — nothing here is a hand-copied
 * hex literal, per this project's repeated "a hand-maintained list drifts
 * from the real set" lesson (CLAUDE.md, multiple sections).
 *
 * NEVER WRITE AN INTACT ARBITRARY-VALUE CLASS IN THIS FILE. Cytoscape
 * style objects are plain JS, not Tailwind classes — no `bg-[` / `text-[`
 * needle is written or needed here.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, themeBlocks, resolveToken } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const roadmap = readFileSync(path.join(SRC_ROOT, "pages/roadmap.tsx"), "utf8")

/** WCAG 2.1 AA for normal-size text. */
const AA_NORMAL_TEXT = 4.5

const { dark, light } = themeBlocks(css)

/**
 * Parse `const NAME: Record<string, string> = { key: "value", ... }` out of
 * roadmap.tsx source text. Throws if the const is not found or parses to
 * zero keys — same vacuity idiom as the sibling
 * `roadmap-badge-foreground-guard.test.ts`.
 */
function extractMap(name: string): Record<string, string> {
  const declRe = new RegExp(`const ${name}:\\s*Record<string,\\s*string>\\s*=\\s*\\{([\\s\\S]*?)\\n\\}`)
  const m = roadmap.match(declRe)
  if (!m) {
    throw new Error(`roadmap-graph-node-label-contrast-guard: could not find 'const ${name}: Record<string, string> = {...}' in roadmap.tsx — the guard is vacuous`)
  }
  const body = m[1]
  const entries: Record<string, string> = {}
  const entryRe = /(\w+):\s*"([^"]+)"/g
  for (const em of body.matchAll(entryRe)) {
    entries[em[1]] = em[2]
  }
  if (Object.keys(entries).length === 0) {
    throw new Error(`roadmap-graph-node-label-contrast-guard: '${name}' parsed to zero keys — the guard is vacuous`)
  }
  return entries
}

const PHASE_TOKEN = extractMap("PHASE_TOKEN")
const PHASE_FG_TOKEN = extractMap("PHASE_FG_TOKEN")

if (Object.keys(PHASE_TOKEN).sort().join(",") !== Object.keys(PHASE_FG_TOKEN).sort().join(",")) {
  throw new Error(
    `roadmap-graph-node-label-contrast-guard: PHASE_TOKEN keys (${Object.keys(PHASE_TOKEN)}) and PHASE_FG_TOKEN keys (${Object.keys(PHASE_FG_TOKEN)}) diverge`,
  )
}

/** Resolve a background token name (e.g. "--status-warning") to hex for a theme. */
function resolveBgToken(tokenDecl: string, block: string): string {
  const token = tokenDecl.replace(/^--/, "")
  const hex = resolveToken(token, block, dark)
  if (!hex) {
    throw new Error(`roadmap-graph-node-label-contrast-guard: background token --${token} unresolvable`)
  }
  return hex
}

/** Resolve a PHASE_FG_TOKEN value — the literal "white" keyword, or an
 * `--x` custom-property name — to hex for a theme. Mirrors the two-branch
 * resolution buildRoadmapStyle() itself performs (literal vs resolveToken()). */
function resolveFgToken(tok: string, block: string): string {
  if (tok === "white") return "#ffffff"
  const hex = resolveToken(tok.replace(/^--/, ""), block, dark)
  if (!hex) {
    throw new Error(`roadmap-graph-node-label-contrast-guard: FG token ${tok} unresolvable`)
  }
  return hex
}

describe("roadmap graph node-label contrast guard (Phase 218 D-07(3))", () => {
  it("buildRoadmapStyle() wires a per-phase 'color' into every node[phase='…'] selector", () => {
    // The exact regression a revert to the shared base nodeLabelColor would
    // reintroduce: each phase selector must carry its OWN "color" entry,
    // keyed to phaseLabelColor[phase] — not merely rely on the base "node"
    // selector's shared color falling through.
    for (const phase of Object.keys(PHASE_TOKEN)) {
      const re = new RegExp(
        `node\\[phase='${phase}'\\][^}]*style:\\s*\\{[^}]*"color":\\s*phaseLabelColor\\.${phase}`,
      )
      expect(re.test(roadmap), `node[phase='${phase}'] selector is missing a per-phase "color": phaseLabelColor.${phase} entry`).toBe(true)
    }
  })

  it("every phase's graph node label clears AA against that phase's own fill, in both themes", () => {
    const ratios: string[] = []
    for (const theme of ["dark", "light"] as const) {
      const block = theme === "dark" ? dark : light
      for (const phase of Object.keys(PHASE_TOKEN)) {
        const bgHex = resolveBgToken(PHASE_TOKEN[phase], block)
        const fgHex = resolveFgToken(PHASE_FG_TOKEN[phase], block)
        const ratio = contrastRatio(fgHex, bgHex)
        ratios.push(`${phase} (${theme}): fg=${fgHex} bg=${bgHex} -> ${ratio.toFixed(2)}:1`)
        expect(
          ratio,
          `${phase} node label (${theme}): fg=${PHASE_FG_TOKEN[phase]} (${fgHex}) on fill ${PHASE_TOKEN[phase]} (${bgHex}) = ${ratio.toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
      }
    }
    console.log("roadmap-graph-node-label-contrast-guard ratio table:\n" + ratios.join("\n"))
  })
})
