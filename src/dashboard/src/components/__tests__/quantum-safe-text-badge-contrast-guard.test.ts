/**
 * Guard-blind `text-quantum-safe` badge-text contrast guard — Phase 218 plan
 * 218-04 (D-07 fold, D-08).
 *
 * WHAT THIS PROTECTS. Two sites pair the Tailwind theme-class shorthand
 * `text-quantum-safe` with a faint alpha-fill background
 * (`bg-quantum-safe/10` or `/20`) on a light-theme card/page surface:
 * `lib/qramm-constants.ts:38` (`MATURITY_BADGE_CLASS[4]`, the "Optimizing"
 * maturity chip) and `pages/healthcare.tsx:100` (`RISK_BADGE.low`, the
 * "Low Risk" chip). Neither is a `bg-[ hsl(var(--x)) ]` arbitrary-value
 * construct, so `badge-contrast-guard.test.ts`'s `BG_TOKEN_RE` structurally
 * cannot see either site (D-08's Tailwind-shorthand blind spot — the same
 * class this project's `MATURITY_BADGE_CLASS[1..3]`/other shorthand badges
 * fall into, TODO-220 per 218-CANDIDATES.md's Guard-blind triage table).
 *
 * WHY WHITE. 218-CANDIDATES.md ("Collateral" > `--quantum-safe`) measured
 * both sites as text on an EFFECTIVELY-WHITE light-theme page background —
 * the `/10`-`/20` alpha fill is too faint to move the ratio meaningfully,
 * and `badge-contrast-evaluator.ts` itself only ever resolves the bg TOKEN
 * value, never the alpha composite, for sites it CAN see. This guard uses
 * the identical white approximation for consistency with that measurement,
 * and is deliberately LIGHT-THEME ONLY: the dark-theme card is near-black,
 * not white, so a "vs white" dark-theme figure would not describe anything
 * that actually renders and is not part of either site's real failure (the
 * FIX-04 D-02 fold only ever claimed a light-theme repair: 4.41:1 -> 5.96:1).
 *
 * SCOPE IS DERIVED AT RUN TIME. Both source snippets are read straight out
 * of `qramm-constants.ts`/`healthcare.tsx` on every run; a module-scope
 * throw fires if either no longer contains the expected `text-quantum-safe`
 * shorthand, per this project's repeated "a hand-maintained list drifts
 * from the real set" lesson (CLAUDE.md, multiple sections).
 *
 * NEVER WRITE AN INTACT ARBITRARY-VALUE CLASS IN THIS FILE. Both sites use
 * plain Tailwind theme-class shorthand (`text-quantum-safe`,
 * `bg-quantum-safe/20`), not an arbitrary-value class, so none is needed or
 * written here.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, themeBlocks, resolveToken } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")

/** WCAG 2.1 AA for normal-size text. */
const AA_NORMAL_TEXT = 4.5

/** White approximation for the light-theme page/card surface these badges
 * render on — see module docstring's "WHY WHITE" section. */
const APPROX_LIGHT_BG = "#ffffff"

const { light } = themeBlocks(css)

const SITES: Array<{ label: string; fileRel: string; needle: string }> = [
  {
    label: "qramm maturity badge level 4 (Optimizing)",
    fileRel: "lib/qramm-constants.ts",
    needle: "text-quantum-safe",
  },
  {
    label: "healthcare RISK_BADGE.low (Low Risk)",
    fileRel: "pages/healthcare.tsx",
    needle: "text-quantum-safe",
  },
]

// VACUITY — module scope, not inside it(): a refactor that renames either
// site's shorthand class away from `text-quantum-safe` must fail this guard
// loudly, not silently protect nothing.
for (const site of SITES) {
  const abs = path.join(SRC_ROOT, site.fileRel)
  const src = readFileSync(abs, "utf8")
  if (!src.includes(site.needle)) {
    throw new Error(
      `quantum-safe-text-badge-contrast-guard: "${site.needle}" not found in ${site.fileRel} — ${site.label}'s guard is vacuous`,
    )
  }
}

const quantumSafeLightHex = resolveToken("quantum-safe", light, light)
if (!quantumSafeLightHex) {
  throw new Error("quantum-safe-text-badge-contrast-guard: --quantum-safe unresolvable in the light theme")
}

describe("guard-blind text-quantum-safe badge contrast (Phase 218 D-07 fold)", () => {
  for (const site of SITES) {
    it(`${site.label} clears AA in the light theme`, () => {
      const ratio = contrastRatio(quantumSafeLightHex!, APPROX_LIGHT_BG)
      expect(
        ratio,
        `${site.label} (${site.fileRel}): text-quantum-safe ${quantumSafeLightHex} on an effectively-white light-theme surface = ${ratio.toFixed(2)}:1`,
      ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
    })
  }
})
