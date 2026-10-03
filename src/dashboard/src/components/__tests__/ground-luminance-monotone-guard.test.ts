/**
 * Ground luminance monotone guard - Phase 222.1 D-04 (BRAND-08).
 *
 * Palette B leaves every ground token unchanged, so this guard freezes today's
 * ramp (measured from the unmodified index.css on 2026-10-02, with this
 * directory's own luminance()/resolveColor() maths, not copied from research).
 *
 * The rule it enforces for any FUTURE ground change: in the dark theme a
 * ground may only get darker, and in the light theme a ground may only get
 * lighter, than the pre-222.1 ramp. With unchanged foregrounds, a monotone
 * ground cannot make a text-on-ground pair worse.
 *
 * A future ground change that legitimately breaks the rule is an operator
 * design call recorded in BRAND-GUIDELINES; it is not a reason to edit PRE.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { luminance, resolveColor, themeBlocks } from "./color-contrast-helpers"

const css = readFileSync(path.resolve(__dirname, "../../index.css"), "utf8")
const { dark, light } = themeBlocks(css)

const TOLERANCE = 5e-5

type Ramp = Record<string, number>

// Frozen pre-222.1 relative luminances (4 dp), measured from the unmodified index.css.
const PRE: { dark: Ramp; light: Ramp } = {
  dark: {
    "--ds-bg-page": 0.003,
    "--ds-bg-base": 0.0048,
    "--ds-bg-surface": 0.0098,
    "--ds-bg-elevated": 0.0152,
    "--background": 0.0036,
    "--card": 0.0055,
    "--popover": 0.0103,
    "--secondary": 0.0103,
    "--muted": 0.0055,
  },
  light: {
    "--ds-bg-page": 0.9308,
    "--ds-bg-base": 1,
    "--ds-bg-surface": 0.8964,
    "--ds-bg-elevated": 1,
    "--background": 0.9474,
    "--card": 1,
    "--popover": 1,
    "--secondary": 0.8621,
    "--muted": 0.8621,
  },
}

function monotoneViolations(
  theme: "dark" | "light",
  measured: Record<string, number | null | undefined>,
  pre: Ramp,
): string[] {
  const out: string[] = []
  for (const [token, was] of Object.entries(pre)) {
    const now = measured[token]
    if (now === null || now === undefined || Number.isNaN(now)) {
      out.push(`${theme} ${token}: unresolvable`)
    } else if (theme === "dark" && now > was + TOLERANCE) {
      out.push(`${theme} ${token}: lighter (${now.toFixed(4)} > ${was})`)
    } else if (theme === "light" && now < was - TOLERANCE) {
      out.push(`${theme} ${token}: darker (${now.toFixed(4)} < ${was})`)
    }
  }
  return out
}

function measure(block: string, pre: Ramp): Record<string, number | null> {
  const out: Record<string, number | null> = {}
  for (const token of Object.keys(pre)) {
    const c = resolveColor(token, block, dark)
    out[token] = c ? luminance(c) : null
  }
  return out
}

describe("ground luminance monotone guard (Phase 222.1 D-04)", () => {
  it("dark grounds are no lighter than before Phase 222.1 (D-04)", () => {
    expect(monotoneViolations("dark", measure(dark, PRE.dark), PRE.dark)).toEqual([])
  })

  it("light grounds are no darker than before Phase 222.1 (D-04)", () => {
    expect(monotoneViolations("light", measure(light, PRE.light), PRE.light)).toEqual([])
  })

  it("probe: a lightened dark ground is flagged", () => {
    const v = monotoneViolations("dark", { ...measure(dark, PRE.dark), "--ds-bg-base": 0.0148 }, PRE.dark)
    expect(v.join()).toContain("--ds-bg-base")
    expect(v.join()).toContain("lighter")
  })

  it("probe: a darkened light ground is flagged", () => {
    const v = monotoneViolations("light", { ...measure(light, PRE.light), "--ds-bg-surface": 0.85 }, PRE.light)
    expect(v.join()).toContain("--ds-bg-surface")
    expect(v.join()).toContain("darker")
  })

  it("probe: an unresolvable ground token is flagged", () => {
    const v = monotoneViolations("dark", { ...measure(dark, PRE.dark), "--card": null }, PRE.dark)
    expect(v.join()).toContain("--card: unresolvable")
  })

  it("guard is not vacuous: at least 9 grounds per theme are measured", () => {
    const d = Object.values(measure(dark, PRE.dark)).filter((x) => x !== null)
    const l = Object.values(measure(light, PRE.light)).filter((x) => x !== null)
    expect(d.length).toBeGreaterThanOrEqual(9)
    expect(l.length).toBeGreaterThanOrEqual(9)
  })
})
