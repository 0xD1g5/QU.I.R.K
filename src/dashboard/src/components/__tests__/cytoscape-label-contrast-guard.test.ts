/**
 * Cytoscape node-label vs node-fill TOKEN-pair guard - Phase 221 plan 221-02
 * (FIX-05, D-10 / D-12) for cbom.tsx and exposure-map.tsx.
 *
 * Measures TOKEN pairs only. The graphs render to <canvas>, whose text is
 * invisible to axe and to DOM-class scanners; that rendered surface is a
 * named exclusion in UNMEASURED-EXCLUSIONS.md (221-06). Whether a failing
 * token pair is a rendered defect is an operator call (221-04), not decided
 * here. No colour token is changed; failures live in
 * cytoscape-label-contrast-baseline.json (shrink-only, re-pointed to 999.118).
 *
 * Roadmap is NOT re-measured: roadmap-graph-node-label-contrast-guard.test.ts
 * already covers it.
 *
 * Pair sets are derived from page source at run time: cbom's QS_TOKEN map and
 * system-node style block; exposure-map's selector blocks that set a
 * background-color, with the label colour taken from its base `node` selector.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, resolveColor, themeBlocks } from "./color-contrast-helpers"
import { ratchetViolations } from "./contrast-ratchet"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const cbom = readFileSync(path.join(SRC_ROOT, "pages/cbom.tsx"), "utf8")
const expo = readFileSync(path.join(SRC_ROOT, "pages/exposure-map.tsx"), "utf8")
const baseline = JSON.parse(readFileSync(path.join(__dirname, "cytoscape-label-contrast-baseline.json"), "utf8"))
delete baseline._comment

const { dark, light } = themeBlocks(css)
const THEMES = [["dark", dark], ["light", light]] as const

function fail(msg: string): never {
  throw new Error(`cytoscape-label-contrast-guard: ${msg}`)
}

/** `const name = resolveToken("--tok")` declarations within a source slice. */
function localTokens(src: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const m of src.matchAll(/const (\w+)\s*=\s*resolveToken\("(--[\w-]+)"\)/g)) out[m[1]] = m[2]
  return out
}

function qsToken(): Record<string, string> {
  const m = cbom.match(/const QS_TOKEN:\s*Record<string,\s*string>\s*=\s*\{([\s\S]*?)\n\}/)
  if (!m) fail("QS_TOKEN not found in cbom.tsx")
  const out: Record<string, string> = {}
  for (const e of m[1].matchAll(/(?:"([^"]+)"|(\w+)):\s*"(--[\w-]+)"/g)) out[e[1] ?? e[2]] = e[3]
  if (Object.keys(out).length < 4) fail("QS_TOKEN parsed to fewer than 4 entries - vacuous")
  return out
}

/** Pairs: key (without theme) -> [labelToken, fillToken]. */
function pairs(): Record<string, [string, string]> {
  const out: Record<string, [string, string]> = {}
  const cbomFn = cbom.slice(cbom.indexOf("function buildCbomGraphStyle"))
  const cLocal = localTokens(cbomFn)
  const label = cLocal.nodeLabelColor
  if (!label) fail("cbom nodeLabelColor token not found")
  for (const [qs, tok] of Object.entries(qsToken())) out[`cbom|${qs}`] = [label, tok]
  const sys = cbomFn.match(/selector:\s*"node\[nodeType='system'\]"[\s\S]*?style:\s*\{([\s\S]*?)\n\s{6}\}/)
  if (!sys) fail("cbom system-node style block not found")
  const bg = sys[1].match(/"background-color":\s*(\w+)/)
  const fg = sys[1].match(/"color":\s*(\w+)/)
  if (!bg || !fg || !cLocal[bg[1]] || !cLocal[fg[1]]) fail("cbom system-node fill/label tokens not parseable")
  out["cbom|system"] = [cLocal[fg[1]], cLocal[bg[1]]]

  const eFn = expo.slice(expo.indexOf("function buildExposureMapStyle"))
  const eLocal = localTokens(eFn)
  const eLabel = eLocal.nodeLabelColor
  if (!eLabel) fail("exposure-map nodeLabelColor token not found")
  let n = 0
  for (const b of eFn.matchAll(/selector:\s*"([^"]+)",\s*style:\s*\{([\s\S]*?)\n\s{6}\}/g)) {
    const fill = b[2].match(/"background-color":\s*(\w+)/)
    if (!fill) continue
    if (!eLocal[fill[1]]) fail(`exposure-map fill ${fill[1]} not a resolveToken const`)
    out[`exposure-map|${b[1]}`] = [eLabel, eLocal[fill[1]]]
    n++
  }
  if (n < 2) fail("exposure-map parsed fewer than 2 filled node selectors - vacuous")
  return out
}

function measure(): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [key, [labelTok, fillTok]] of Object.entries(pairs())) {
    for (const [theme, block] of THEMES) {
      const l = resolveColor(labelTok, block, dark)
      const f = resolveColor(fillTok, block, dark)
      if (!l || !f || !l.startsWith("#") || !f.startsWith("#")) fail(`cannot resolve ${key} ${theme}: ${l} / ${f}`)
      out[`${key}|${theme}`] = Math.round(contrastRatio(l, f) * 100) / 100
    }
  }
  return out
}

describe("Cytoscape label/fill token-pair contrast (221-02)", () => {
  it("derives pairs from page source at run time (vacuity floor)", () => {
    expect(Object.keys(pairs()).length).toBeGreaterThanOrEqual(7)
  })

  it("measures both themes for every pair", () => {
    expect(Object.keys(measure()).length).toBe(Object.keys(pairs()).length * 2)
  })

  it("holds the shrink-only ratchet against cytoscape-label-contrast-baseline.json", () => {
    const v = ratchetViolations(measure(), baseline)
    expect(v, v.join("\n")).toEqual([])
  })

  it("probe: the ratchet used here flags a worsened pair", () => {
    expect(ratchetViolations({ "cbom|system|light": 1 }, { "cbom|system|light": 1.26 }).join()).toContain("worsened")
  })
})
