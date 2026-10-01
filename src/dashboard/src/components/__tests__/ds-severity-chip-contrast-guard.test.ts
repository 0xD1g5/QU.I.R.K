/**
 * DS severity-chip family contrast guard - Phase 221 plan 221-02 (FIX-05,
 * D-10 / D-12).
 *
 * BLIND SPOT. RATCHET-01's evaluator cannot see `.severity-*-chip` (CSS
 * classes in index.css, not Tailwind bg-[...] utilities), so its empty
 * baseline says nothing about them. This guard MEASURES them.
 *
 * Chip set is discovered from index.css at run time (vacuity floor 5).
 * For each theme x chip x surface: text = --ds-<chip> of that theme;
 * background = --ds-<chip>-dim (the .light block does not redefine -dim, so
 * it falls back to the dark rgba tint) alpha-blended over the surface token.
 * Surface assumption: the only consumer is qramm/QuestionCard.tsx, which sits
 * in a shadcn <Card> (bg-card), not directly on a --ds-bg-* token, so BOTH
 * --ds-bg-base and --ds-bg-surface are measured as bounding cases.
 *
 * No colour token is changed here. Failing pairs live in
 * ds-chip-contrast-baseline.json (shrink-only; re-pointed to 999.118).
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { blendOver, contrastRatio, resolveColor, themeBlocks } from "./color-contrast-helpers"
import { ratchetViolations } from "./contrast-ratchet"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const baseline = JSON.parse(readFileSync(path.join(__dirname, "ds-chip-contrast-baseline.json"), "utf8"))
delete baseline._comment

const { dark, light } = themeBlocks(css)
const SURFACES = ["--ds-bg-base", "--ds-bg-surface"]

const chips = [...new Set([...css.matchAll(/\.severity-([a-z]+)-chip\b/g)].map((m) => m[1]))].sort()

function measure(): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [theme, block] of [["dark", dark], ["light", light]] as const) {
    for (const chip of chips) {
      const text = resolveColor(`--ds-${chip}`, block, dark)
      const dim = resolveColor(`--ds-${chip}-dim`, block, dark)
      if (!text || !dim) throw new Error(`ds chip guard: cannot resolve ${chip} in ${theme}`)
      for (const surface of SURFACES) {
        const s = resolveColor(surface, block, dark)
        if (!s) throw new Error(`ds chip guard: cannot resolve ${surface} in ${theme}`)
        out[`${theme}|${chip}|${surface}`] = Math.round(contrastRatio(text, blendOver(dim, s)) * 100) / 100
      }
    }
  }
  return out
}

describe("DS severity-chip family contrast (221-02)", () => {
  it("discovers the chip family from index.css at run time (vacuity floor)", () => {
    expect(chips.length).toBeGreaterThanOrEqual(5)
  })

  it("measures every theme x chip x surface pair", () => {
    expect(Object.keys(measure()).length).toBe(chips.length * 2 * SURFACES.length)
  })

  it("holds the shrink-only ratchet against ds-chip-contrast-baseline.json", () => {
    const v = ratchetViolations(measure(), baseline)
    expect(v, v.join("\n")).toEqual([])
  })

  it("baseline keys are well-formed and below 4.5", () => {
    for (const [k, v] of Object.entries(baseline)) {
      expect(k).toMatch(/^(dark|light)\|[a-z]+\|--ds-bg-(base|surface)$/)
      expect(v as number).toBeLessThan(4.5)
    }
  })

  it("blendOver composites alpha per channel", () => {
    expect(blendOver("rgba(75, 168, 168, 0.12)", "#0d0f14")).toBe("#142126")
    expect(blendOver("#abcdef", "#000000")).toBe("#abcdef")
    expect(() => blendOver("nonsense", "#000000")).toThrow()
  })

  it("probe: ratchet flags a new failing pair", () => {
    expect(ratchetViolations({ "a|b": 3 }, {}).join()).toContain("new failing pair")
  })
  it("probe: ratchet flags a worsened pair", () => {
    expect(ratchetViolations({ "a|b": 3 }, { "a|b": 3.5 }).join()).toContain("worsened")
  })
  it("probe: ratchet flags a fixed pair that must be deleted", () => {
    expect(ratchetViolations({ "a|b": 5 }, { "a|b": 3.5 }).join()).toContain("delete it from the baseline")
  })
  it("probe: ratchet flags an orphan baseline key", () => {
    expect(ratchetViolations({}, { "a|b": 3.5 }).join()).toContain("orphan")
  })
  it("probe: ratchet passes a held pair and a passing pair", () => {
    expect(ratchetViolations({ "a|b": 3.5, "c|d": 6 }, { "a|b": 3.5 })).toEqual([])
  })
})
