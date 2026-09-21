import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { luminance, contrastRatio, hslToHex } from "./color-contrast-helpers"

// Phase 165 CR-01 regression guard.
//
// `.label-eyebrow` renders at 10px — normal-size text under WCAG, so AA
// requires 4.5:1, not the 3:1 large-text allowance. It resolves its color as
// `var(--ds-text-muted, hsl(var(--muted-foreground)))`. Because
// `--ds-text-muted` is defined in BOTH theme blocks, that fallback can never
// fire: `--ds-text-muted` is the value that actually ships, and a fix applied
// only to `--muted-foreground` is silently shadowed.
//
// That is exactly what happened during Phase 165: D-10 corrected
// `--muted-foreground` from 50% to 52% lightness, but `.label-eyebrow` kept
// rendering the old failing `#6e7a95` (4.46:1 on card bg). The axe sweep could
// not catch it — the only consumers (LifecycleEventRow, VendorTrendRow) live
// on /hardware and /compare, and neither route is in tests/a11y/routes.json.
//
// This guard closes both halves: it asserts the shipped token clears AA
// against the surfaces it actually renders on, in both themes, without
// depending on route coverage.

const CSS_PATH = path.resolve(__dirname, "../../index.css")
const css = readFileSync(CSS_PATH, "utf8")

/**
 * Extract every declaration of a custom property, in source order.
 * Index 0 is the dark (`:root`) block, index 1 the light-theme block —
 * matching index.css's dark-first token layout.
 */
function declarations(token: string): string[] {
  const re = new RegExp(`--${token}:\\s*(#[0-9a-fA-F]{6})\\s*;`, "g")
  return [...css.matchAll(re)].map((m) => m[1].toLowerCase())
}

const AA_NORMAL_TEXT = 4.5

describe("muted design-token contrast (Phase 165 CR-01 guard)", () => {
  it("declares --ds-text-muted in both theme blocks", () => {
    // If this drops to one declaration the fallback semantics change and the
    // rest of this suite would be asserting against the wrong value.
    expect(declarations("ds-text-muted")).toHaveLength(2)
  })

  it("clears AA for .label-eyebrow on dark surfaces", () => {
    const [dark] = declarations("ds-text-muted")
    // The two backgrounds .label-eyebrow actually renders on in dark theme.
    const cardBg = "#0d0f14" // --ds-bg-base / --card
    expect(contrastRatio(dark, cardBg)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("clears AA for .label-eyebrow on light surfaces", () => {
    const [, light] = declarations("ds-text-muted")
    expect(contrastRatio(light, "#ffffff")).toBeGreaterThanOrEqual(
      AA_NORMAL_TEXT,
    )
  })

  it("keeps --ds-text-muted no darker than --muted-foreground on dark theme", () => {
    // The shadowing bug: --ds-text-muted wins, so it must never be the dimmer
    // of the pair. A future fix applied only to --muted-foreground will trip
    // this instead of shipping silently.
    const [dark] = declarations("ds-text-muted")
    const mutedFgHsl = css.match(/--muted-foreground:\s*([\d.]+)\s+([\d.]+)%\s+([\d.]+)%/)
    expect(mutedFgHsl).not.toBeNull()
    const mutedFgLuminance = luminance(hslToHex(
      Number(mutedFgHsl![1]),
      Number(mutedFgHsl![2]),
      Number(mutedFgHsl![3]),
    ))
    expect(luminance(dark)).toBeGreaterThanOrEqual(mutedFgLuminance - 1e-6)
  })
})

