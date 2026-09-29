/**
 * Single derived source-file set for the dashboard's style-audit guards —
 * Phase 215 plan 215-01 (RATCHET-03).
 *
 * SCOPE IS DERIVED AT RUN TIME, NEVER WRITTEN DOWN. `auditedFiles()` below
 * performs a recursive `readdirSync` walk of `src/` at import time and
 * returns every non-test `.tsx` file it finds. A page, component or panel
 * added tomorrow is audited tomorrow with zero edits here. This repository
 * has been bitten repeatedly by hand-maintained file lists drifting from the
 * real set (see CLAUDE.md's staleness-review discipline) — a written list is
 * not a safeguard, only a derivation is.
 *
 * Not a `*.test.ts` file, so vitest's include glob
 * (`src/** /__tests__/** /*.{test,spec}.{ts,tsx}`) does not collect it as a
 * suite — same idiom as the sibling `color-contrast-helpers.ts` (see its own
 * docstring). Consumers import `auditedFiles()` and run their own assertions
 * inside their own test files.
 *
 * `stripComments()` LIVES HERE ONCE, extracted from exactly TWO verbatim
 * copies: `hardcoded-color-audit.test.tsx` and `theme-token-vocabulary.test.ts`
 * (the latter's own comment reads "Same comment-stripping logic as
 * hardcoded-color-audit.test.tsx" — an explicit admission of the duplication
 * this module closes).
 *
 * THREE OTHER `stripComments`-shaped functions exist elsewhere in this
 * codebase and are DELIBERATELY left alone, not folded in here:
 *   - `lifecycle-advisory-guard.test.ts` — line-prefix filtering only, no
 *     block-comment handling.
 *   - `vendor-trend-advisory-guard.test.ts` — same shape as the above; that
 *     file's own comment records the duplication as deliberate.
 *   - `src/pages/__tests__/exposure-map-colors.test.ts` — a third, separate
 *     implementation.
 * These are different implementations serving a different concern than the
 * two extracted here. Folding any of them into this module would change
 * those guards' behaviour. A reader who wants to "finish the job" and
 * collapse all five into one function would be wrong to do so — do not.
 *
 * A reader citing "stripComments is deduplicated" WITHOUT the qualification
 * above (two of five, not five of five) would be citing this module
 * incorrectly.
 */
import { readdirSync } from "node:fs"
import path from "node:path"

export const SRC_ROOT = path.resolve(__dirname, "../..")

/**
 * Recursively walk `SRC_ROOT`, collecting every `.tsx` file that is not a
 * `*.test.tsx` file and does not live under a `__tests__` directory. Returns
 * paths relative to `SRC_ROOT`, sorted.
 */
function walk(dir: string): string[] {
  const found: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (entry.name === "__tests__") continue
      found.push(...walk(path.join(dir, entry.name)))
      continue
    }
    if (!entry.name.endsWith(".tsx")) continue
    if (entry.name.endsWith(".test.tsx")) continue
    found.push(path.relative(SRC_ROOT, path.join(dir, entry.name)))
  }
  return found
}

const AUDITED_ALL: readonly string[] = walk(SRC_ROOT).sort()

/**
 * All non-test `.tsx` files under `src/`, derived fresh at import time.
 * Returns a copy on every call so a consumer cannot mutate the shared set.
 */
export function auditedFiles(): string[] {
  return [...AUDITED_ALL]
}

/**
 * Blank out comment bodies so a comment that merely *discusses* a colour or
 * token is not reported as a violation, while keeping line numbering intact.
 * Line comments are only stripped when `//` opens the line, so a `//` inside
 * a string literal (a URL, say) cannot swallow real code.
 *
 * Byte-identical to the body formerly duplicated in
 * `hardcoded-color-audit.test.tsx` and `theme-token-vocabulary.test.ts` — do
 * not "improve" it; both consumers depend on its exact current behaviour.
 */
export function stripComments(src: string): string {
  const noBlocks = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
  return noBlocks
    .split("\n")
    .map((line) => (/^\s*\/\//.test(line) ? "" : line))
    .join("\n")
}

// VACUITY — asserted at module scope (collection time), not inside an it().
// A throw here is a collection error no wrapper can absorb, so a broken walk
// can never masquerade as "no violations found" over an empty set. Floors,
// never exact-count equalities: HARNESS-03 exists precisely because an
// exact-count pin flaked between macOS and CI, and D-04 locks this project
// against repeating that mistake here.
if (AUDITED_ALL.length < 60) {
  throw new Error(
    `audited-files: recursive walk returned only ${AUDITED_ALL.length} files — ` +
      "fewer than src/ actually contains. The walk is broken.",
  )
}
if (!AUDITED_ALL.includes(path.join("components", "sidebar.tsx"))) {
  throw new Error("audited-files: components/sidebar.tsx is missing from the audited set")
}
if (AUDITED_ALL.filter((f) => f.startsWith(`pages${path.sep}`)).length < 20) {
  throw new Error(
    `audited-files: only ${AUDITED_ALL.filter((f) => f.startsWith(`pages${path.sep}`)).length} ` +
      "pages/ files resolved — src/pages/ has far more than that",
  )
}
