/**
 * DS severity-chip family contrast guard - Phase 221 plan 221-02 (FIX-05,
 * D-10 / D-12).
 *
 * BLIND SPOT. RATCHET-01's evaluator cannot see `.severity-*-chip` (CSS
 * classes in index.css, not Tailwind arbitrary-value background utilities), so its empty
 * baseline says nothing about them. This guard MEASURES them.
 *
 * Chip set is discovered from index.css at run time (vacuity floor 5), and
 * cross-checked against the count of every `-chip {` rule so it cannot shrink
 * silently (221 WR-08: a hyphenated `.severity-very-high-chip` was invisible to
 * the former `[a-z]+` discovery).
 * For each theme x chip x surface: text and background are the tokens the chip
 * RULE itself names in its `color:` and `background:` declarations (221 WR-08:
 * never assumed from the naming convention); the .light block does not redefine
 * the -dim tints, so they fall back to the dark rgba tint, alpha-blended over
 * the surface token.
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

// 221 WR-08: parse each chip rule body and take the custom property its declarations reference.
const CHIP_RULE = /\.severity-([a-z][\w-]*?)-chip\s*\{([^}]*)\}/g
const chipRules = [...css.matchAll(CHIP_RULE)].map((m) => ({ chip: m[1], body: m[2] }))
const chips = [...new Set(chipRules.map((r) => r.chip))].sort()
const allChipRuleHeads = [...css.matchAll(/-chip\s*\{/g)].length

function declVar(chip: string, body: string, prop: "color" | "background"): string {
  const propRe = prop === "color" ? "color" : "background(?:-color)?"
  const m = body.match(new RegExp(`(?:^|[;\\s])${propRe}\\s*:\\s*([^;]+);?`))
  if (!m) throw new Error(`ds chip guard: .severity-${chip}-chip has no ${prop} declaration`)
  const v = m[1].trim().match(/^var\((--[\w-]+)\)$/)
  if (!v) throw new Error(`ds chip guard: .severity-${chip}-chip ${prop} is not a single var(--token): ${m[1].trim()}`)
  return v[1]
}

const chipTokens = Object.fromEntries(
  chipRules.map((r) => [r.chip, { text: declVar(r.chip, r.body, "color"), bg: declVar(r.chip, r.body, "background") }]),
)

function measure(): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [theme, block] of [["dark", dark], ["light", light]] as const) {
    for (const chip of chips) {
      const text = resolveColor(chipTokens[chip].text, block, dark)
      const dim = resolveColor(chipTokens[chip].bg, block, dark)
      if (!text || !dim) throw new Error(`ds chip guard: cannot resolve ${chip} in ${theme}`)
      // 221 WR-07: contrastRatio needs opaque hex; a translucent text token would measure NaN.
      if (!text.startsWith("#")) throw new Error(`ds chip guard: ${chip} text in ${theme} is not opaque hex: ${text}`)
      for (const surface of SURFACES) {
        const s = resolveColor(surface, block, dark)
        if (!s) throw new Error(`ds chip guard: cannot resolve ${surface} in ${theme}`)
        if (!s.startsWith("#")) throw new Error(`ds chip guard: ${surface} in ${theme} is not opaque hex: ${s}`)
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

  it("discovers every -chip rule in index.css, so the chip set cannot shrink silently (221 WR-08)", () => {
    expect(chipRules.length, "a .severity-<x>-chip selector is declared more than once").toBe(chips.length)
    expect(chips.length, `${allChipRuleHeads} "-chip {" rules in index.css but ${chips.length} severity chips discovered`).toBe(allChipRuleHeads)
  })

  it("reads text and background from each chip rule's own declarations (221 WR-08)", () => {
    for (const chip of chips) {
      expect(chipTokens[chip].text, `${chip} color token`).toMatch(/^--[\w-]+$/)
      expect(chipTokens[chip].bg, `${chip} background token`).toMatch(/^--[\w-]+$/)
    }
    // live index.css today: the convention holds, so the measured pairs are unchanged by WR-08
    expect(chipTokens.critical).toEqual({ text: "--ds-critical", bg: "--ds-critical-dim" })
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
      expect(k).toMatch(/^(dark|light)\|[a-z][\w-]*\|--ds-bg-(base|surface)$/)
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
  it("probe: ratchet flags a non-finite ratio, new or baselined (221 WR-07)", () => {
    expect(ratchetViolations({ "a|b": NaN }, {}).join()).toContain("non-finite")
    expect(ratchetViolations({ "a|b": NaN }, { "a|b": 3.5 }).join()).toContain("non-finite")
    expect(ratchetViolations({ "a|b": Infinity }, {}).join()).toContain("non-finite")
  })
  it("probe: every measured ratio is finite", () => {
    for (const [k, r] of Object.entries(measure())) expect(Number.isFinite(r), `${k} = ${r}`).toBe(true)
  })
  it("probe: ratchet passes a held pair and a passing pair", () => {
    expect(ratchetViolations({ "a|b": 3.5, "c|d": 6 }, { "a|b": 3.5 })).toEqual([])
  })
})
