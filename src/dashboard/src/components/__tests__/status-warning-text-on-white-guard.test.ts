/**
 * Text-on-white contrast guard for the ONE surviving TEXT-USE occurrence of
 * `--status-warning` / `--chart-tls` — Phase 217 plan 217-02 (D-08/D-09).
 *
 * WHAT THIS PROTECTS. Phase 213 minted `.light` overrides for both tokens
 * specifically so they clear AA 4.5:1 AS TEXT ON A WHITE SURFACE: index.css's
 * own comment on `--status-warning`'s light value reads "#9d6607, 4.84:1 —
 * see note above", and the note explains the dark literal (#f59f0a) is only
 * 2.13:1 on white, so the light override is a deliberate improvement, not a
 * faithful port. `217-SPIKE.md`'s mechanical classification (D-04) found
 * exactly ONE live call site that uses either token this way —
 * `certificates.tsx`'s `daysToExpiry < 90` branch — everything else is
 * either a badge background (29 sites) or a non-class token/chart reference
 * (9 sites). That single site is what this guard exists to protect.
 *
 * WHY IT MATTERS NOW. Plan 217-03 (wave 2, after this plan) mints new
 * `--status-warning-foreground` / `--chart-tls-foreground` tokens and
 * bulk-edits the 29 BADGE-BACKGROUND sites to consume them. That is a
 * search-and-replace-shaped change across 10 pages; nothing before this
 * guard existed stops an overzealous replace from also touching
 * `certificates.tsx:87` and repointing it at the new `-foreground` token —
 * which would be WRONG for this site (it is not a badge background, it has
 * no adjacent `bg-`, and D-08 requires the base tokens' OWN values to stay
 * exactly what they are, unchanged, in both themes). No existing guard
 * covers this: `cbom-badge-contrast-guard.test.ts` and
 * `badge-contrast-guard.test.ts` only ever look at `bg-`/`text-` BADGE
 * pairs extracted from source, never a bare `text-` utility with no
 * companion `bg-`.
 *
 * SCOPE IS DERIVED AT RUN TIME. The `daysToExpiry` branch text and the
 * `.light`/dark `--status-warning`/`--chart-tls` values are read straight
 * out of `certificates.tsx` and `index.css` on every run, never copied into
 * this file as a hand-maintained literal — the collection-time vacuity
 * checks below fail loudly if either source stops matching what this guard
 * expects to find, per this project's repeated "a hand-maintained list
 * drifts from the real set" lesson (CLAUDE.md, multiple sections).
 *
 * NEVER WRITE AN INTACT ARBITRARY-VALUE CLASS IN THIS FILE. Tailwind's JIT
 * scanner does a static regex pass over raw source text, including comments
 * and string literals, across every file the `content` glob covers — which
 * is every file under `__tests__`, not just shipped component source. Every
 * needle below is assembled by string concatenation for exactly this
 * reason; see `cbom-badge-contrast-guard.test.ts`'s own docstring for the
 * two times this repo's build broke over it.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, themeBlocks, resolveToken } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const certificates = readFileSync(path.join(SRC_ROOT, "pages/certificates.tsx"), "utf8")

/** WCAG 2.1 AA for normal-size text. */
const AA_NORMAL_TEXT = 4.5

// Needles built by concatenation — never an intact "prefix-[ ... ]" candidate in this file.
const BARE_STATUS_WARNING_TEXT_NEEDLE = "text-" + "[hsl(var(--status-warning))]"
const FOREGROUND_STATUS_WARNING_TEXT_NEEDLE = "text-" + "[hsl(var(--status-warning-foreground))]"

const { dark, light } = themeBlocks(css)

// VACUITY — asserted at collection time, not inside an it(). A refactor that stops
// matching either source must fail loudly, not report a silent pass over nothing.
if (!/daysToExpiry/.test(certificates)) {
  throw new Error(
    "certificates.tsx no longer contains 'daysToExpiry' — the protected branch this guard " +
      "targets may have moved or been renamed. The guard is vacuous.",
  )
}
if (!/--status-warning:/.test(dark)) {
  throw new Error("index.css dark block parse failed for --status-warning — the guard is vacuous")
}
if (!/--status-warning:/.test(light)) {
  throw new Error("index.css light block parse failed for --status-warning — the guard is vacuous")
}
if (!/--chart-tls:/.test(dark)) {
  throw new Error("index.css dark block parse failed for --chart-tls — the guard is vacuous")
}
if (!/--chart-tls:/.test(light)) {
  throw new Error("index.css light block parse failed for --chart-tls — the guard is vacuous")
}

describe("status-warning / chart-tls text-on-white guard (Phase 217 D-08/D-09)", () => {
  it("certificates.tsx's daysToExpiry<90 branch still resolves to the BARE --status-warning token", () => {
    // Narrow the search to a short window starting at the daysToExpiry branch, so a
    // coincidental match elsewhere in the file cannot pass this test by accident.
    const idx = certificates.indexOf("daysToExpiry < 90")
    expect(idx, "daysToExpiry < 90 branch not found in certificates.tsx").toBeGreaterThan(-1)
    const window = certificates.slice(idx, idx + 200)

    expect(
      window.includes(BARE_STATUS_WARNING_TEXT_NEEDLE),
      "the daysToExpiry<90 branch no longer uses the bare --status-warning text token",
    ).toBe(true)

    expect(
      window.includes(FOREGROUND_STATUS_WARNING_TEXT_NEEDLE),
      "the daysToExpiry<90 branch has been repointed to the -foreground token — this is the " +
        "protected text-on-white use, D-08 requires it stay on the BARE token",
    ).toBe(false)
  })

  it("--status-warning's light value on white stays >= AA 4.5:1 (today 4.84:1)", () => {
    const hex = resolveToken("status-warning", light, dark)
    expect(hex, "--status-warning unresolvable in the light theme block").not.toBeNull()
    const ratio = contrastRatio(hex!, "#ffffff")
    expect(
      ratio,
      `--status-warning ${hex} on white = ${ratio.toFixed(2)}:1 — Phase 213's text-on-white fix regressed`,
    ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("--chart-tls's light value on white stays >= AA 4.5:1 (today 6.26:1)", () => {
    const hex = resolveToken("chart-tls", light, dark)
    expect(hex, "--chart-tls unresolvable in the light theme block").not.toBeNull()
    const ratio = contrastRatio(hex!, "#ffffff")
    expect(
      ratio,
      `--chart-tls ${hex} on white = ${ratio.toFixed(2)}:1 — Phase 213's text-on-white fix regressed`,
    ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })
})
