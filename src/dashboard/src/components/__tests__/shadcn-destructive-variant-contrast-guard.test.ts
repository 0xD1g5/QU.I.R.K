/**
 * shadcn destructive Badge/Button variant contrast guard — Phase 218 plan
 * 218-04 (D-07(2)).
 *
 * WHAT THIS PROTECTS. `components/ui/badge.tsx`'s and `components/ui/button.tsx`'s
 * `destructive` variant both consume the Tailwind theme-class shorthand
 * `bg-destructive text-destructive-foreground` — a pure token pairing with no
 * arbitrary-value class, so `badge-contrast-guard.test.ts`'s
 * `BG_TOKEN_RE` (`bg-\[hsl(var(--…\)\)\]`) structurally cannot see either site
 * (D-08's Tailwind-shorthand blind spot). Before FIX-04 D-01, `--destructive`
 * (dark) + `--destructive-foreground` (dark, static white) measured 3.82:1 —
 * failing AA — in every consumer of either variant app-wide (executive.tsx,
 * scan-job.tsx, schedules.tsx, qramm-profile.tsx, qramm-assessment.tsx —
 * confirmed live in 218-CANDIDATES.md's Collateral section).
 *
 * SCOPE IS DERIVED AT RUN TIME. Both variant class strings are read straight
 * out of `badge.tsx`/`button.tsx` on every run, never hand-copied here. A
 * missing `destructive:` variant in either file is a vacuity throw at module
 * scope, not a silently-skipped `it()`.
 *
 * NEVER WRITE AN INTACT ARBITRARY-VALUE CLASS IN THIS FILE. Both sites under
 * test use plain Tailwind theme-class shorthand (`bg-destructive`,
 * `text-destructive-foreground`), not an arbitrary-value class, so none is
 * needed or written here.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, themeBlocks, resolveToken } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")

/** WCAG 2.1 AA for normal-size text. */
const AA_NORMAL_TEXT = 4.5

const { dark, light } = themeBlocks(css)

/**
 * Extract the `destructive:` variant class string out of a shadcn `cva(...)`
 * definition. Throws if the variant is missing — a renamed/removed variant
 * must fail this guard loudly, not silently protect nothing.
 */
function extractDestructiveVariant(fileRel: string): string {
  const abs = path.join(SRC_ROOT, fileRel)
  const src = readFileSync(abs, "utf8")
  const m = src.match(/destructive:\s*\n?\s*"([^"]+)"/)
  if (!m) {
    throw new Error(
      `shadcn-destructive-variant-contrast-guard: no 'destructive:' variant class string found in ${fileRel} — the guard is vacuous`,
    )
  }
  return m[1]
}

/** Resolve the bg token name from a variant class string. `bg-destructive` ->
 * "destructive"; an arbitrary `bg-[hsl(var(--x))]` -> "x". Throws on anything
 * else — an unresolvable bg is a hard failure, never silently skipped. */
function resolveBgTokenName(classes: string): string {
  const arbitrary = classes.match(/bg-\[hsl\(var\(--([\w-]+)\)\)\]/)
  if (arbitrary) return arbitrary[1]
  if (/\bbg-destructive\b/.test(classes)) return "destructive"
  throw new Error(`shadcn-destructive-variant-contrast-guard: unresolvable bg token in "${classes}"`)
}

/** Resolve the fg token name from a variant class string. `text-destructive-foreground`
 * -> "destructive-foreground"; an arbitrary `text-[hsl(var(--x))]` -> "x";
 * `text-white`/`text-black` -> the literal hex. Throws on anything else. */
function resolveFg(classes: string, block: string, fallback: string): string {
  if (/\btext-white\b/.test(classes)) return "#ffffff"
  if (/\btext-black\b/.test(classes)) return "#000000"
  const arbitrary = classes.match(/text-\[hsl\(var\(--([\w-]+)\)\)\]/)
  const tokenName = arbitrary ? arbitrary[1] : (/\btext-destructive-foreground\b/.test(classes) ? "destructive-foreground" : null)
  if (!tokenName) {
    throw new Error(`shadcn-destructive-variant-contrast-guard: unresolvable fg token in "${classes}"`)
  }
  const hex = resolveToken(tokenName, block, fallback)
  if (!hex) {
    throw new Error(`shadcn-destructive-variant-contrast-guard: --${tokenName} unresolvable`)
  }
  return hex
}

const BADGE_VARIANT = extractDestructiveVariant("components/ui/badge.tsx")
const BUTTON_VARIANT = extractDestructiveVariant("components/ui/button.tsx")

const BADGE_BG_TOKEN = resolveBgTokenName(BADGE_VARIANT)
const BUTTON_BG_TOKEN = resolveBgTokenName(BUTTON_VARIANT)

describe("shadcn destructive variant contrast guard (Phase 218 D-07(2))", () => {
  it("shadcn destructive Badge variant clears AA in both themes", () => {
    for (const [themeName, block] of [["dark", dark], ["light", light]] as const) {
      const bgHex = resolveToken(BADGE_BG_TOKEN, block, dark)
      if (!bgHex) throw new Error(`shadcn-destructive-variant-contrast-guard: --${BADGE_BG_TOKEN} unresolvable (${themeName})`)
      const fgHex = resolveFg(BADGE_VARIANT, block, dark)
      const ratio = contrastRatio(fgHex, bgHex)
      expect(
        ratio,
        `badge.tsx destructive variant (${themeName}): fg=${fgHex} bg=${bgHex} = ${ratio.toFixed(2)}:1`,
      ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
    }
  })

  it("shadcn destructive Button variant clears AA in both themes", () => {
    for (const [themeName, block] of [["dark", dark], ["light", light]] as const) {
      const bgHex = resolveToken(BUTTON_BG_TOKEN, block, dark)
      if (!bgHex) throw new Error(`shadcn-destructive-variant-contrast-guard: --${BUTTON_BG_TOKEN} unresolvable (${themeName})`)
      const fgHex = resolveFg(BUTTON_VARIANT, block, dark)
      const ratio = contrastRatio(fgHex, bgHex)
      expect(
        ratio,
        `button.tsx destructive variant (${themeName}): fg=${fgHex} bg=${bgHex} = ${ratio.toFixed(2)}:1`,
      ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
    }
  })
})
