/**
 * Repo-wide badge-contrast guard — Phase 215 plan 215-03 (RATCHET-01 / RATCHET-02).
 *
 * WHAT THIS MEASURES. Every non-test `.tsx` file under `src/` (via `auditedFiles()`,
 * 76 files as of Phase 215-01/RATCHET-03), scanned file-wide for a Tailwind
 * arbitrary-value background utility naming a CSS custom property paired, in the same
 * quoted class string, with a `text-white` / `text-black` / arbitrary-value text
 * utility. Each pair is evaluated in BOTH themes against `index.css`'s dark (`:root`)
 * and light (`.light`) blocks. This is verbatim the extraction method backlog
 * 999.117 used ("103 pairs across 11 files"), so this guard's output is directly
 * comparable to that filed measurement — see the count decomposition below.
 *
 * THIS GUARD FIXES NOTHING. Every failing pair found is either a fresh violation
 * (fails CI immediately) or a recorded, justified entry in the checked-in
 * `badge-contrast-baseline.json` sibling file. No token value and no shipped `.tsx`
 * is touched by this file or by executing it.
 *
 * `cbom-badge-contrast-guard.test.ts` IS DELIBERATELY RETAINED ALONGSIDE THIS GUARD
 * (D-01). That file is Phase 213-07 regression provenance — its docstring records
 * what broke, why three other gates missed it, and the Tailwind JIT hazard this file
 * also has to respect. Its narrower `QS_BADGE`-literal parse (`badgePairs()`) is NOT
 * superseded by this file's file-wide scan; the overlap on `cbom.tsx` between the two
 * guards is intentional redundancy, not duplication to resolve. Do not delete or fold
 * in `cbom-badge-contrast-guard.test.ts` because this file exists.
 *
 * WHY 45 DOES NOT EQUAL THE BASELINE'S ENTRY COUNT. ROADMAP.md / REQUIREMENTS.md cite
 * "45" for this debt, which counts RAW FAILING OCCURRENCES over the pages+sidebar
 * (11-file) set 999.117 measured. This guard's baseline is keyed
 * `file|bgToken|fgSpec|theme` (D-06 — no line numbers, because Phase 217 will shift
 * every one of them wholesale while fixing badge contrast). That key deduplicates
 * identical class strings repeated within one file and splits per theme, so the
 * checked-in baseline holds fewer, DISTINCT entries than 45 raw occurrences. Both "45"
 * and the baseline's entry count are correct measurements of two different things; see
 * `215-03-SUMMARY.md` for the live re-derivation of both figures and the exact delta.
 *
 * VACUITY IS ASSERTED AT MODULE SCOPE (COLLECTION TIME), NEVER INSIDE AN it(), AND
 * AGAINST FLOORS, NEVER EXACT COUNTS. A throw here is a collection error no wrapper
 * can absorb into a false pass — a regex that stops matching a refactored `index.css`
 * or page file must fail loudly, never silently report perfect contrast over zero
 * pairs. Floors, not equalities, because HARNESS-03 (this project's own history) is a
 * live flake caused by exactly that kind of exact-count pin flaking between macOS and
 * CI; D-04 locks this guard against repeating that mistake.
 *
 * TAILWIND JIT HAZARD. `tailwind.config.ts`'s content glob covers every file under
 * `src/components/__tests__/`, including this one. An intact arbitrary-value class
 * string anywhere in this file — even inside a comment, even naming a nonexistent
 * token — gets scanned as a real candidate and can emit a junk rule into the shipped
 * stylesheet. This has broken the build TWICE already, the second time from an
 * example written inside the very comment warning about it
 * (`cbom-badge-contrast-guard.test.ts:34-48`). Every class-shaped construct in this
 * file that is not a real, escaped regex literal breaks its brackets with an interior
 * space, e.g. `bg-[ hsl(var(--token)) ]` in prose — never write one intact.
 */
import { describe, it, expect } from "vitest"
import { existsSync, readFileSync, writeFileSync } from "node:fs"
import path from "node:path"
import { auditedFiles, SRC_ROOT, stripComments } from "./audited-files"
import { themeBlocks, resolveToken } from "./color-contrast-helpers"
import { extractPairs, evaluatePairs, findStaleBaselineKeys, type BadgePair } from "./badge-contrast-evaluator"
// .mjs import into a vitest .ts file needs no shim — confirmed live during Phase 215
// planning (215-RESEARCH.md § Code Examples: tests/a11y/baseline-diff.test.ts runs 31
// passing tests doing exactly this). Reused rather than minting a second predicate (D-10).
// @ts-expect-error — .mjs has no ambient type declaration; vitest/esbuild resolve it
// fine with zero config change (confirmed live, 215-RESEARCH.md § Code Examples), and
// `tsc -b` does not include tests/a11y/ at all so this only affects this import's type.
import { isPlaceholderJustification } from "../../../tests/a11y/baseline-diff.mjs"

type BaselineEntry = { ratio: number; why: string }
type Baseline = Record<string, BaselineEntry>

const BASELINE_PATH = path.join(__dirname, "badge-contrast-baseline.json")
const IS_REGENERATING = process.env.UPDATE_BADGE_CONTRAST_BASELINE === "1"

// --- Derive the pair set from source, at module scope, on every run. ---------------

const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const { dark, light } = themeBlocks(css)

const files = auditedFiles()
const pairs: BadgePair[] = []
for (const file of files) {
  const raw = readFileSync(path.join(SRC_ROOT, file), "utf8")
  const stripped = stripComments(raw)
  pairs.push(...extractPairs(stripped, file))
}

const THEMES = ["dark", "light"] as const

// Resolve every distinct token name (background tokens, plus any "--token" foreground
// specs) against both theme blocks, falling back to the dark block per index.css's
// dark-first structure (theme-invariant tokens are declared once).
function distinctTokenNames(): string[] {
  const names = new Set<string>()
  for (const p of pairs) {
    names.add(p.bgToken)
    if (p.fgSpec.startsWith("--")) names.add(p.fgSpec.slice(2))
  }
  return [...names]
}

const tokenNames = distinctTokenNames()
const tokens: Record<string, Record<string, string>> = { dark: {}, light: {} }
for (const name of tokenNames) {
  const darkHex = resolveToken(name, dark, dark)
  const lightHex = resolveToken(name, light, dark)
  if (darkHex) tokens.dark[name] = darkHex
  if (lightHex) tokens.light[name] = lightHex
}

// --- VACUITY — module scope, collection time, floors only (D-04). ------------------
//
// These throws exist because a regex that silently stops matching (a refactored
// index.css, a page rewritten away from the arbitrary-value idiom) must fail loudly,
// never report perfect contrast over an empty pair set. They are FLOORS, never exact
// counts: HARNESS-03 is a real, documented flake in this project caused by exactly an
// exact-count pin disagreeing between macOS and CI, and D-04 forbids repeating that
// mistake here. Planning measured 103 raw pair occurrences across 11 contributing
// files; the floors below are set comfortably under that so ordinary badge additions
// or removals never trip them, while a genuinely broken extraction still does.

if (pairs.length < 80) {
  throw new Error(
    `badge-contrast-guard: extracted only ${pairs.length} badge pairs across the audited ` +
      "file set — fewer than expected. The extraction regex has likely stopped matching " +
      "real source (e.g. a Tailwind class idiom changed). The guard is vacuous.",
  )
}

const contributingFiles = new Set(pairs.map((p) => p.file))
if (contributingFiles.size < 8) {
  throw new Error(
    `badge-contrast-guard: only ${contributingFiles.size} distinct files contributed a badge ` +
      "pair — fewer than expected. The guard is vacuous.",
  )
}

if (!/--qs-node-safe:/.test(dark)) {
  throw new Error("badge-contrast-guard: dark theme block parse failed — the guard is vacuous")
}
if (!/--status-warning:/.test(light)) {
  throw new Error("badge-contrast-guard: light theme block parse failed — the guard is vacuous")
}

if (Object.keys(tokens.dark).length === 0) {
  throw new Error("badge-contrast-guard: zero dark-theme tokens resolved — the guard is vacuous")
}
if (Object.keys(tokens.light).length === 0) {
  throw new Error("badge-contrast-guard: zero light-theme tokens resolved — the guard is vacuous")
}

if (!existsSync(BASELINE_PATH) && !IS_REGENERATING) {
  throw new Error(
    "badge-contrast-guard: badge-contrast-baseline.json is missing. A missing baseline must " +
      "not silently evaluate as an empty one. Run with UPDATE_BADGE_CONTRAST_BASELINE=1 to " +
      "generate it, then write a real justification for every entry.",
  )
}

const existingBaseline: Baseline = existsSync(BASELINE_PATH)
  ? JSON.parse(readFileSync(BASELINE_PATH, "utf8"))
  : {}

// --- Regeneration — gated, never automatic (D-08). ----------------------------------
//
// A baseline that rewrites itself on a red run is the silent-widening failure
// RATCHET-02 exists to forbid, so this path is unreachable unless the operator sets
// UPDATE_BADGE_CONTRAST_BASELINE to exactly "1". Existing justifications are preserved
// for any key already present; a brand-new key gets an obviously-invalid placeholder
// so a regenerated-but-unjustified entry fails the justification test until a human
// writes a real reason.
if (IS_REGENERATING) {
  const failuresAgainstEmpty = evaluatePairs(pairs, tokens, {})
  const regenerated: Baseline = {}
  for (const f of failuresAgainstEmpty) {
    if (f.kind !== "new" || f.ratio === null) continue
    const prior = existingBaseline[f.key]
    regenerated[f.key] = {
      ratio: f.ratio,
      why: prior ? prior.why : "PLACEHOLDER — replace with a real justification (999.117 class + ratio).",
    }
  }
  const sortedKeys = Object.keys(regenerated).sort()
  const sorted: Baseline = {}
  for (const k of sortedKeys) sorted[k] = regenerated[k]
  writeFileSync(BASELINE_PATH, `${JSON.stringify(sorted, null, 2)}\n`, "utf8")
}

const baseline: Baseline = IS_REGENERATING
  ? (JSON.parse(readFileSync(BASELINE_PATH, "utf8")) as Baseline)
  : existingBaseline

const failures = evaluatePairs(pairs, tokens, baseline)
const byKind = {
  unresolvable: failures.filter((f) => f.kind === "unresolvable"),
  new: failures.filter((f) => f.kind === "new"),
  worsened: failures.filter((f) => f.kind === "worsened"),
  fixed: failures.filter((f) => f.kind === "fixed"),
}
const staleKeys = findStaleBaselineKeys(baseline, pairs, [...THEMES])

// In regeneration mode every it.skipIf(IS_REGENERATING) node below is skipped, not
// failed — the suite "exits without asserting" exactly as D-08 requires, without a
// separate always-passing node whose only job would be to exist. The baseline write
// above already happened at module scope by the time vitest reaches this describe.
describe("repo-wide badge contrast (RATCHET-01 / RATCHET-02)", () => {
  it.skipIf(IS_REGENERATING)(
    "every extracted pair resolves to a background and foreground colour in both themes",
    () => {
      expect(
        byKind.unresolvable.map((f) => f.detail),
        `${byKind.unresolvable.length} pair(s) could not be resolved to a colour in at least one theme`,
      ).toEqual([])
    },
  )

  it.skipIf(IS_REGENERATING)("no badge pair is below AA outside the recorded baseline", () => {
    expect(
      byKind.new.map((f) => f.detail),
      `${byKind.new.length} new sub-AA badge pair(s) found, not covered by the baseline. ` +
        "Either fix the colour or add a justified baseline entry (never a placeholder).",
    ).toEqual([])
  })

  it.skipIf(IS_REGENERATING)("no baselined pair has worsened below its recorded ceiling", () => {
    expect(
      byKind.worsened.map((f) => f.detail),
      `${byKind.worsened.length} baselined pair(s) worsened below their recorded ratio ceiling`,
    ).toEqual([])
  })

  it.skipIf(IS_REGENERATING)(
    "no baselined pair has been silently fixed — a fixed pair must have its entry deleted",
    () => {
      expect(
        byKind.fixed.map((f) => f.detail),
        `${byKind.fixed.length} baselined pair(s) now clear AA. This is GOOD NEWS: delete ` +
          "the named entry from badge-contrast-baseline.json and let the normal assertion " +
          "guard it — do not relax or widen the gate to accommodate a fix.",
      ).toEqual([])
    },
  )

  it.skipIf(IS_REGENERATING)("every baseline entry names a pair that still exists", () => {
    expect(
      staleKeys,
      `${staleKeys.length} baseline key(s) match no live pair/theme combination and should be deleted`,
    ).toEqual([])
  })

  it.skipIf(IS_REGENERATING)("every baseline entry carries a real justification", () => {
    const rejected = Object.entries(baseline)
      .filter(([, entry]) => isPlaceholderJustification(entry.why))
      .map(([key]) => key)
    expect(
      rejected,
      `${rejected.length} baseline entr(y/ies) carry a placeholder or too-short justification`,
    ).toEqual([])
  })
})
