/**
 * CBOM quantum-safety badge contrast guard — Phase 213 regression (v5.25 audit).
 *
 * WHAT BROKE. Plan 213-07 (`3f50b104`) tokenised `cbom.tsx`'s QS_BADGE map,
 * substituting `--qs-node-safe` for the literal `hsl(142 71% 30%)`:
 *
 *     - Safe: "bg-[ hsl(142_71%_30%) ] text-white"           #16833e + white = 4.84:1  PASS
 *     + Safe: "bg-[ hsl(var(--qs-node-safe)) ] text-white"    #21c45d + white = 2.30:1  FAIL
 *
 *   (The spaces inside the brackets are deliberate — see NOTE ON SPACING below.)
 *
 * Same hue, same saturation, lightness 30% -> 45% — and lightness is the one
 * channel contrast depends on. The 30% was not arbitrary: `4d18cdf4`
 * (165-04, "flip teal/severity foregrounds to AA-clearing dark tokens")
 * darkened it deliberately to clear 4.5:1, landing at 4.84 with a thin
 * margin. `--qs-node-safe` is a Cytoscape NODE FILL token, never intended to
 * sit behind text; its own paired `--qs-node-safe-foreground` is near-black.
 *
 * WHY NOTHING CAUGHT IT. 213's own `hardcoded-color-audit.test.tsx` passed —
 * it asks "is this a literal?", not "does this contrast?". Tokenisation
 * therefore launders an accessibility fix into a token reference that looks
 * correct in review. The axe sweep DID catch the dark-theme half, but only
 * after the fact, and only because /cbom happens to be in routes.json.
 *
 * WHAT AXE STILL CANNOT CATCH. `run-a11y.mjs` sweeps the default (dark)
 * fixture variant only, so a light-theme-only contrast failure is invisible
 * to it. This guard found exactly one: "At Risk" resolves to
 * `--status-warning` = `38 92% 32%` (#9d6607) in `.light`, which with
 * `text-black` is 4.34:1. That token's own index.css comment reads
 * "#9d6607, 4.84:1" — the ratio it achieves as TEXT ON WHITE, its designed
 * use. QS_BADGE reuses it as a BACKGROUND, where that number does not apply.
 * Same shape as the miss recorded in `muted-token-contrast-guard.test.ts`.
 *
 * NOTE ON SPACING. Tailwind's JIT scanner does a static regex pass over raw source text
 * INCLUDING comments and string literals — cbom.tsx carries its own warning about this, and
 * records that a build failed twice over it, the second time from an example written into
 * that very comment. The same thing happened here: an intact arbitrary-value class in this
 * docstring, naming a token that does not exist, was scanned as a real candidate and emitted
 * a junk rule into the shipped stylesheet. Hence the spaces inside the brackets above; they
 * break the candidate while keeping the diff readable. Never write an intact arbitrary-value
 * class in this file, not even to describe one.
 *
 * SCOPE IS DERIVED AT RUN TIME, NEVER WRITTEN DOWN. The badge pairs are
 * parsed out of `cbom.tsx` and the token values out of `index.css` on every
 * run, so a future badge, state or token rename is covered automatically. A
 * hand-maintained list here would be the very thing this project has been
 * bitten by repeatedly.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, hslToHex } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const cbom = readFileSync(path.join(SRC_ROOT, "pages/cbom.tsx"), "utf8")

/** WCAG 2.1 AA for normal-size text. The badge renders at `text-xs` (12px). */
const AA_NORMAL_TEXT = 4.5

/**
 * index.css is dark-first: `:root { … }` holds the dark palette, `.light { … }`
 * overrides it. Split on `.light {` — every colour token in this file is
 * declared in one or both of those two blocks.
 */
function themeBlocks(): { dark: string; light: string } {
  const lightStart = css.indexOf(".light {")
  expect(lightStart).toBeGreaterThan(-1)
  return { dark: css.slice(0, lightStart), light: css.slice(lightStart) }
}

/**
 * Resolve an `--x` token to hex within a theme block, falling back to the
 * dark block when the light block does not override it (theme-invariant
 * tokens such as `--qs-node-safe` are declared once).
 */
function resolveToken(token: string, block: string, fallback: string): string | null {
  const re = new RegExp(`--${token}:\\s*([\\d.]+)\\s+([\\d.]+)%\\s+([\\d.]+)%`)
  const m = block.match(re) ?? fallback.match(re)
  if (!m) return null
  return hslToHex(Number(m[1]), Number(m[2]), Number(m[3]))
}

/** Parse the QS_BADGE literal out of cbom.tsx: state -> Tailwind class string. */
function badgePairs(): Array<{ state: string; classes: string }> {
  const block = cbom.match(/const QS_BADGE:\s*Record<string,\s*string>\s*=\s*\{([\s\S]*?)\n\}/)
  expect(block).not.toBeNull()
  return [...block![1].matchAll(/["']?([\w\s]+?)["']?\s*:\s*"([^"]+)"/g)].map((m) => ({
    state: m[1].trim(),
    classes: m[2],
  }))
}

/** Foreground hex for a Tailwind text-* utility used in QS_BADGE. */
function foregroundHex(classes: string, block: string, fallback: string): string | null {
  if (/\btext-white\b/.test(classes)) return "#ffffff"
  if (/\btext-black\b/.test(classes)) return "#000000"
  const tok = classes.match(/text-\[hsl\(var\(--([\w-]+)\)\)\]/)
  return tok ? resolveToken(tok[1], block, fallback) : null
}

/** Background token name for a Tailwind arbitrary-value background utility. */
function backgroundToken(classes: string): string | null {
  const m = classes.match(/bg-\[hsl\(var\(--([\w-]+)\)\)\]/)
  return m ? m[1] : null
}

const pairs = badgePairs()
const { dark, light } = themeBlocks()

// VACUITY — asserted at collection time, not inside an it(). A regex that
// stops matching a refactored cbom.tsx or index.css must fail loudly rather
// than report perfect contrast over zero badges.
if (pairs.length === 0) throw new Error("QS_BADGE parse yielded zero badges — the guard is vacuous")
if (!/--qs-node-safe:/.test(dark)) throw new Error("dark block parse failed — the guard is vacuous")
if (!/--status-warning:/.test(light)) throw new Error("light block parse failed — the guard is vacuous")

/**
 * KNOWN GAPS — ratcheted, not silenced.
 *
 * A gap here is asserted to STILL FAIL at no worse than its recorded ratio. So it trips in
 * both directions: if the pair degrades further the ceiling breaks, and if someone fixes it
 * the "still failing" assertion breaks and this entry must be deleted. That is the vitest
 * analogue of the `xfail(strict=True)` this repo uses on the Python side — the same reason
 * `test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` is strict.
 *
 * This is NOT a place to park the regression this file exists to catch. Only pre-existing,
 * separately-filed defects belong here.
 */
const KNOWN_GAPS: Record<string, { ratio: number; why: string }> = {
  "At Risk|light": {
    ratio: 4.34,
    why:
      "--status-warning resolves to 38 92% 32% (#9d6607) in .light, and QS_BADGE pairs it with " +
      "a static text-black => 4.34:1. The light value was minted by 213-02 as a TEXT colour on " +
      "white (its index.css comment reads '#9d6607, 4.84:1' — that ratio is against white, its " +
      "designed use); QS_BADGE reuses it as a BACKGROUND, where the number does not carry. " +
      "Not fixable by swapping the static foreground: near-black passes dark (7.99) but fails " +
      "light (3.52); white passes light (4.84) but fails dark (1.94). It needs a theme-varying " +
      "--status-warning-foreground token, which affects ~14 call sites across 8 pages. " +
      "The axe sweep cannot see this: run-a11y.mjs sweeps the default (dark) variant only. " +
      "Tracked as backlog 999.117 (dashboard-accessibility-debt), deferred as one unit.",
  },
}

describe("cbom QS_BADGE contrast (Phase 213-07 tokenisation regression)", () => {
  it("parses every badge as a resolvable bg-token / foreground pair", () => {
    for (const { state, classes } of pairs) {
      expect(backgroundToken(classes), `${state}: no arbitrary-value background utility`).not.toBeNull()
      expect(foregroundHex(classes, dark, dark), `${state}: no resolvable foreground`).not.toBeNull()
    }
  })

  describe.each([
    ["dark", dark],
    ["light", light],
  ])("%s theme", (themeName, block) => {
    it.each(pairs.map((p) => [p.state, p.classes]))(
      "%s badge clears AA 4.5:1",
      (state, classes) => {
        const bgToken = backgroundToken(classes)!
        const bg = resolveToken(bgToken, block, dark)
        const fg = foregroundHex(classes, block, dark)
        expect(bg, `${state}: --${bgToken} unresolvable`).not.toBeNull()
        expect(fg, `${state}: foreground unresolvable`).not.toBeNull()
        const ratio = contrastRatio(bg!, fg!)
        const detail = `${state} (${themeName}): bg ${bg} (--${bgToken}) on fg ${fg} = ${ratio.toFixed(2)}:1`

        const gap = KNOWN_GAPS[`${state}|${themeName}`]
        if (gap) {
          expect(ratio, `${detail} — known gap WORSENED. ${gap.why}`).toBeGreaterThanOrEqual(
            gap.ratio - 0.01,
          )
          expect(
            ratio,
            `${detail} — known gap appears FIXED. Delete this KNOWN_GAPS entry and let the ` +
              `normal assertion guard it. ${gap.why}`,
          ).toBeLessThan(AA_NORMAL_TEXT)
          return
        }

        expect(ratio, detail).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
      },
    )
  })

  it("every KNOWN_GAPS entry names a badge/theme pair that actually exists", () => {
    // A stale entry (state renamed, badge deleted) would silently excuse nothing while
    // reading as a live exemption. Same anti-drift rule as the rest of this file.
    const live = new Set(pairs.flatMap((p) => [`${p.state}|dark`, `${p.state}|light`]))
    for (const key of Object.keys(KNOWN_GAPS)) {
      expect(live.has(key), `KNOWN_GAPS["${key}"] matches no badge in QS_BADGE`).toBe(true)
    }
  })
})
