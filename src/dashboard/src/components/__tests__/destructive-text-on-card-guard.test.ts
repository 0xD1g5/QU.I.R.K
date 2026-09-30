/**
 * Text-on-card contrast guard for `text-destructive` used as TEXT (not a
 * badge background) — Phase 218 plan 218-02 (D-10).
 *
 * WHAT THIS PROTECTS. `--destructive` is a dual-use token: it is a badge
 * BACKGROUND (paired with `text-white`/`text-destructive-foreground`,
 * measured 3.82:1 in dark today and tracked as a FIX-04 baseline key), and
 * it is separately used as bare `text-destructive` TEXT directly on `--card`
 * in a run-time-derived number of files (scan-job, scan-new, login,
 * schedules, qramm-profile, compare, print, RegressionAlertChip,
 * ScorecardTab, ComplianceMapTab, scan-history — see the collected list
 * below). Today that text use measures ~4.95:1 (dark) / ~5.59:1 (light) on
 * `--card` — comfortably above AA.
 *
 * WHY IT MATTERS NOW. Phase 218's CONTEXT D-01 explicitly excluded darkening
 * `--destructive` itself to fix the badge pairs, because doing so would drop
 * this SAME token's text-on-card use below AA (L60 -> L49 measures 3.68:1).
 * That exclusion is only real if something actually fails when someone
 * ignores it later — this guard is that something.
 *
 * SCOPE IS DERIVED AT RUN TIME. The set of files using bare `text-destructive`
 * (as opposed to `text-destructive-foreground`, a different token entirely)
 * is grep'd out of `src/pages` + `src/components` on every run, never
 * hand-copied into this file, per this project's repeated "a hand-maintained
 * list drifts from the real set" lesson (CLAUDE.md, multiple sections). The
 * module-scope vacuity check below throws if that scan ever finds zero
 * files, so a refactor that renamed every site away from the bare token
 * would fail this guard loudly rather than let it pass over nothing.
 *
 * NEVER WRITE AN INTACT ARBITRARY-VALUE CLASS IN THIS FILE. Tailwind's JIT
 * scanner does a static regex pass over raw source text, including comments
 * and string literals, across every file the `content` glob covers —
 * including this directory. No needle in this file is written as an intact
 * "prefix-[ ... ]" token; none is needed here since `text-destructive` is a
 * plain Tailwind theme-class utility, not an arbitrary value.
 */
import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, statSync } from "node:fs"
import path from "node:path"
import { contrastRatio, themeBlocks, resolveToken } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const CSS_PATH = path.join(SRC_ROOT, "index.css")
const css = readFileSync(CSS_PATH, "utf8")

/** WCAG 2.1 AA for normal-size text. */
const AA_NORMAL_TEXT = 4.5

/** Bare `text-destructive`, NOT `text-destructive-foreground`. */
const BARE_TEXT_DESTRUCTIVE_RE = /\btext-destructive\b(?!-foreground)/

/** Recursively walk a directory, returning .tsx/.ts files (never __tests__). */
function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) {
      if (entry === "__tests__" || entry === "node_modules") continue
      walk(full, out)
    } else if (/\.tsx?$/.test(entry)) {
      out.push(full)
    }
  }
  return out
}

const CANDIDATE_FILES = [
  ...walk(path.join(SRC_ROOT, "pages")),
  ...walk(path.join(SRC_ROOT, "components")),
]

const SITES = CANDIDATE_FILES.filter((f) => BARE_TEXT_DESTRUCTIVE_RE.test(readFileSync(f, "utf8")))

let dark: string
let light: string
try {
  ;({ dark, light } = themeBlocks(css))
} catch (e) {
  throw new Error(`destructive-text-on-card-guard: themeBlocks(index.css) failed — ${(e as Error).message}`)
}

// VACUITY — asserted at collection time, not inside an it(). A refactor that
// stops matching either source must fail loudly, not report a silent pass
// over nothing.
if (SITES.length === 0) {
  throw new Error(
    "destructive-text-on-card-guard: zero files under src/pages + src/components contain a " +
      "bare `text-destructive` utility — the protected site set is empty and the guard is vacuous.",
  )
}

const destructiveDark = resolveToken("destructive", dark, dark)
const destructiveLight = resolveToken("destructive", light, dark)
const cardDark = resolveToken("card", dark, dark)
const cardLight = resolveToken("card", light, dark)

if (!destructiveDark) throw new Error("destructive-text-on-card-guard: --destructive unresolvable in the dark theme")
if (!destructiveLight) throw new Error("destructive-text-on-card-guard: --destructive unresolvable in the light theme")
if (!cardDark) throw new Error("destructive-text-on-card-guard: --card unresolvable in the dark theme")
if (!cardLight) throw new Error("destructive-text-on-card-guard: --card unresolvable in the light theme")

// Recorded for the SUMMARY — not asserted as a fixed literal, since the
// count is derived at run time (today: 11 files).
console.log(
  `destructive-text-on-card-guard: ${SITES.length} bare text-destructive site(s): ` +
    SITES.map((f) => path.relative(SRC_ROOT, f)).join(", "),
)

describe("text-destructive on --card guard (Phase 218 D-10)", () => {
  it("text-destructive on --card clears AA in the dark theme", () => {
    const ratio = contrastRatio(destructiveDark!, cardDark!)
    expect(
      ratio,
      `--destructive ${destructiveDark} on --card ${cardDark} (dark) = ${ratio.toFixed(2)}:1`,
    ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })

  it("text-destructive on --card clears AA in the light theme", () => {
    const ratio = contrastRatio(destructiveLight!, cardLight!)
    expect(
      ratio,
      `--destructive ${destructiveLight} on --card ${cardLight} (light) = ${ratio.toFixed(2)}:1`,
    ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
  })
})
