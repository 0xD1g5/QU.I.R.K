import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// Phase 185 tooltip-contrast regression guard.
//
// Reported by the operator via screenshot on 2026-09-06: on the Severity
// Breakdown chart, the bar label (e.g. `HIGH`) rendered legibly while the
// series item text (`count : 2`) was effectively invisible — dark text on a
// dark panel. Root cause at `executive.tsx:385-388`: `contentStyle` and
// `labelStyle` were hand-set, but `itemStyle` was never set at all, so
// Recharts' `DefaultTooltipContent` fell back to its own dark default for
// the series text. One sub-part was themed; its sibling was forgotten.
//
// The fix drives all three colors (`contentStyle` background/border,
// `labelStyle` color, `itemStyle` color) from the existing
// `--popover` / `--popover-foreground` / `--border` design tokens, which are
// declared in BOTH theme blocks of index.css. This guard is a static source
// check, not a Puppeteer hover or a jsdom render:
//   - A Puppeteer hover step inside run-a11y.mjs would render new DOM nodes
//     into the axe scan of the `/` route, perturbing the existing root
//     baseline's counts for a change this phase does not intend to make.
//   - A jsdom render performs no CSS cascade resolution on inline literal
//     style props (React's `style={{...}}` values are passed through
//     verbatim), so it would return exactly the same string this guard reads
//     directly from source — for zero additional confidence and much more
//     machinery.
// Reading the source text of executive.tsx and index.css directly gets the
// same answer for free, in both themes, with zero DOM.

const TSX_PATH = path.resolve(__dirname, "../../pages/executive.tsx")
const CSS_PATH = path.resolve(__dirname, "../../index.css")
const tsx = readFileSync(TSX_PATH, "utf8")
const css = readFileSync(CSS_PATH, "utf8")

/** Relative luminance per WCAG 2.1 §Relative luminance. */
function luminance(hex: string): number {
  const h = hex.replace("#", "")
  const channels = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const linear = channels.map((c) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4),
  )
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

/** Contrast ratio per WCAG 2.1 §Contrast ratio. */
function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/** Minimal HSL->hex, sufficient for the token values in index.css. */
function hslToHex(h: number, s: number, l: number): string {
  const sN = s / 100
  const lN = l / 100
  const c = (1 - Math.abs(2 * lN - 1)) * sN
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = lN - c / 2
  const seg = Math.floor(h / 60) % 6
  const [r, g, b] = [
    [c, x, 0],
    [x, c, 0],
    [0, c, x],
    [0, x, c],
    [x, 0, c],
    [c, 0, x],
  ][seg]
  const toHex = (v: number) =>
    Math.round((v + m) * 255)
      .toString(16)
      .padStart(2, "0")
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

/**
 * Extract every declaration of a custom property, in source order.
 * Index 0 is the dark (`:root`) block, index 1 the light-theme block —
 * matching index.css's dark-first token layout. Token values here are
 * `H S% L%` triples, not `#rrggbb` literals.
 */
function declarationsHex(token: string): string[] {
  const re = new RegExp(`--${token}:\\s*([\\d.]+)\\s+([\\d.]+)%\\s+([\\d.]+)%\\s*;`, "g")
  return [...css.matchAll(re)].map((m) =>
    hslToHex(Number(m[1]), Number(m[2]), Number(m[3])),
  )
}

/** Extract the `<Tooltip ... />` element's full source text from executive.tsx. */
function tooltipBlock(): string {
  const match = tsx.match(/<Tooltip\b[\s\S]*?\/>/)
  if (!match) {
    throw new Error("executive-tooltip-contrast-guard: could not find a <Tooltip /> element in executive.tsx")
  }
  return match[0]
}

/** Extract the token name referenced by `hsl(var(--token))` inside a style prop's value. */
function tokenRefFor(block: string, propName: string): string | null {
  const propRe = new RegExp(`${propName}=\\{\\{[\\s\\S]*?\\}\\}`)
  const propMatch = block.match(propRe)
  if (!propMatch) return null
  const tokenMatch = propMatch[0].match(/hsl\(var\(--([a-zA-Z0-9-]+)\)\)/)
  return tokenMatch ? tokenMatch[1] : null
}

const AA_NORMAL_TEXT = 4.5

describe("Severity Breakdown tooltip contrast (Phase 185 guard)", () => {
  const block = tooltipBlock()

  it("sets itemStyle on the Tooltip (2026-09-06 regression: series text `count : N` rendered dark-on-dark while the label above it was legible)", () => {
    expect(block).toMatch(/itemStyle=/)
  })

  const contentBgToken = tokenRefFor(block, "contentStyle")
  const labelToken = tokenRefFor(block, "labelStyle")
  const itemToken = tokenRefFor(block, "itemStyle")

  it("resolves contentStyle background from a design token", () => {
    expect(contentBgToken).not.toBeNull()
  })

  it("resolves labelStyle color from a design token", () => {
    expect(labelToken).not.toBeNull()
  })

  it("resolves itemStyle color from a design token", () => {
    expect(itemToken).not.toBeNull()
  })

  it.each([
    ["contentStyle background", () => contentBgToken],
    ["labelStyle color", () => labelToken],
    ["itemStyle color", () => itemToken],
  ])("%s's referenced token is declared in both theme blocks", (_name, getToken) => {
    const token = getToken()
    expect(token).not.toBeNull()
    expect(declarationsHex(token as string)).toHaveLength(2)
  })

  it("itemStyle color clears AA against contentStyle background in the dark theme block", () => {
    const [dark] = declarationsHex(contentBgToken as string)
    const [darkItem] = declarationsHex(itemToken as string)
    expect(contrastRatio(darkItem, dark)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("itemStyle color clears AA against contentStyle background in the light theme block", () => {
    const [, light] = declarationsHex(contentBgToken as string)
    const [, lightItem] = declarationsHex(itemToken as string)
    expect(contrastRatio(lightItem, light)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("labelStyle color clears AA against contentStyle background in the dark theme block", () => {
    const [dark] = declarationsHex(contentBgToken as string)
    const [darkLabel] = declarationsHex(labelToken as string)
    expect(contrastRatio(darkLabel, dark)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("labelStyle color clears AA against contentStyle background in the light theme block", () => {
    const [, light] = declarationsHex(contentBgToken as string)
    const [, lightLabel] = declarationsHex(labelToken as string)
    expect(contrastRatio(lightLabel, light)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("has no raw non-token hsl(N N% N%) triple in the Tooltip element's props", () => {
    // Matches an hsl() literal that is NOT immediately followed by `var(` —
    // i.e. a hand-set literal like the pre-fix `hsl(240 6% 10%)`.
    const rawLiteral = /hsl\(\s*(?!var\()[\d.]+\s+[\d.]+%\s+[\d.]+%\s*\)/
    expect(block).not.toMatch(rawLiteral)
  })
})
