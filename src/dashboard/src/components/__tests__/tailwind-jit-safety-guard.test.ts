/**
 * Tailwind JIT safety guard — Phase 215 plan 215-04.
 *
 * THE HAZARD. `tailwind.config.ts`'s `content` glob is `./src/**\/*.{ts,tsx,js,jsx}`,
 * which covers every file under every `__tests__` directory, not just shipped
 * component source. The Tailwind JIT scanner does a static regex pass over that raw
 * source text — including comments and string literals — so an intact arbitrary-value
 * utility class written ANYWHERE in a `__tests__` file, even inside a docstring
 * describing the hazard, gets scanned as a real candidate and can emit a junk rule
 * into the shipped stylesheet. This has broken the build TWICE: once from a stray
 * example, and the second time from an example written inside the very comment
 * warning about the first (`cbom-badge-contrast-guard.test.ts:34-48`).
 *
 * WHY NOTHING CAUGHT THIS UNTIL NOW. The convention that has protected this repo so
 * far — "break the candidate with spaces inside the brackets, e.g. `bg-[ hsl(...) ]`"
 * — has only ever been enforced by per-file docstring discipline. `215-RESEARCH.md`
 * confirmed no ESLint plugin, no custom test and no pre-commit hook mechanically
 * enforces it. A convention that lives only in prose is not a safeguard; this guard
 * replaces it with a mechanical check.
 *
 * WHAT THIS GUARD SCANS. Every file under `src/` that sits inside a directory named
 * `__tests__` and ends `.ts` or `.tsx`, walked recursively at collection time (never
 * a hand-maintained list — this project has been bitten by those repeatedly). It
 * detects a Tailwind arbitrary-value class CANDIDATE: a lowercase utility prefix (one
 * or more hyphen-separated segments) immediately followed by an opening square
 * bracket that is NOT itself preceded by a backslash, a run containing neither
 * whitespace nor a closing bracket, then a closing bracket. The no-whitespace
 * requirement is what makes the spaces-inside-brackets convention a valid escape — a
 * construct written with an interior space is not a JIT candidate and correctly
 * produces no hit. The unescaped-bracket requirement is what keeps this guard from
 * false-positiving on the many JS regex literals in these files (e.g.
 * `badge-contrast-evaluator.ts`'s own `BG_TOKEN_RE`), where the bracket is written
 * escaped as `\[`.
 *
 * MEASURED STARTING STATE (2026-09-28, `215-RESEARCH.md` / this plan's own
 * `<interfaces>`): the identical unescaped-bracket-candidate scan returns 303 hits
 * across all of `src/`, every one of them a legitimate class in shipped component
 * source — and ZERO hits inside any `__tests__` directory. That is what makes scoping
 * this guard to `src/**\/__tests__/**\/*.{ts,tsx}` safe to land green today, with no
 * false positives and no allowlist required.
 *
 * WHAT THIS GUARD DOES NOT SCAN. Shipped component source outside `__tests__`
 * (where real arbitrary-value classes correctly live), and the 36 bracket constructs
 * under `tests/a11y/` that live in `.json`/`.md` files outside Tailwind's content glob
 * — both are correctly out of scope.
 */
import { describe, it, expect } from "vitest"
import { readdirSync, readFileSync, statSync } from "node:fs"
import path from "node:path"

const SRC_ROOT = path.resolve(__dirname, "../..")

// Utility prefix: a lowercase leading segment, zero or more further hyphen-joined
// segments, then a MANDATORY trailing hyphen directly before the bracket -- real
// Tailwind arbitrary-value utilities are always written `<prefix>-[ value ]`, with the
// hyphen sitting immediately before the bracket (`bg-[ ... ]`, `top-[ ... ]`,
// `grid-cols-[ ... ]`). Requiring that trailing hyphen is what excludes false positives
// like a JS array index (`calls[0]`), a property-access string (`style["color"]`), or
// a hyphenated identifier immediately followed by an unrelated bracket construct
// (`data-ready['"]` inside a regex literal) -- none of those have a hyphen directly
// before the bracket. The prefix must also not be preceded by a closing bracket `]`
// (a word sitting directly after another bracket group is chained regex/selector
// syntax, not a Tailwind class, which always starts at a quote or whitespace
// boundary), and the opening bracket itself must NOT be preceded by a backslash
// (which would mean this is an escaped bracket inside a JS regex literal). The run
// inside the brackets contains no whitespace and no closing bracket -- the
// no-whitespace requirement is the escape hatch the spaces-inside-brackets convention
// relies on.
const ARBITRARY_VALUE_CANDIDATE_RE = /\b(?<!\])[a-z][a-z0-9]*(?:-[a-z0-9]+)*-(?<!\\)\[[^\s\]]+\]/g

interface Hit {
  file: string
  line: number
  candidate: string
}

/** Every file under `dir` (recursively) whose name ends in the given suffixes. */
function walkFiles(dir: string, suffixes: string[]): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    const st = statSync(full)
    if (st.isDirectory()) {
      out.push(...walkFiles(full, suffixes))
    } else if (suffixes.some((suf) => entry.endsWith(suf))) {
      out.push(full)
    }
  }
  return out
}

/** Every `__tests__`-directory `.ts`/`.tsx` file under `src/`, derived at collection
 * time — never a hand-maintained list. */
function testsDirFiles(): string[] {
  return walkFiles(SRC_ROOT, [".ts", ".tsx"]).filter((f) =>
    f.split(path.sep).includes("__tests__"),
  )
}

/** Scan one file's text for arbitrary-value class candidates, formatted `file:line`. */
function findCandidates(fileText: string, fileLabel: string): Hit[] {
  const hits: Hit[] = []
  const lines = fileText.split("\n")
  lines.forEach((lineText, idx) => {
    for (const m of lineText.matchAll(ARBITRARY_VALUE_CANDIDATE_RE)) {
      hits.push({ file: fileLabel, line: idx + 1, candidate: m[0] })
    }
  })
  return hits
}

const TEST_FILES = testsDirFiles()

// Vacuity floor (D-04): a guard that scans zero files and reports zero violations is
// worse than no guard. A floor, not an equality — this repo's own HARNESS-03 history
// is what an exact-count pin does when the file set shifts between machines.
if (TEST_FILES.length < 10) {
  throw new Error(
    `Tailwind JIT safety guard collected only ${TEST_FILES.length} __tests__ files ` +
      "(floor: 10). The walk or the __tests__ directory structure may have changed; " +
      "investigate before trusting a green run from this guard.",
  )
}

describe("Tailwind JIT safety guard -- no intact arbitrary-value class in any __tests__ file", () => {
  it(`scans every __tests__ .ts/.tsx file under src/ (collected ${TEST_FILES.length} files) and finds no intact arbitrary-value class`, () => {
    const allHits: string[] = []
    for (const file of TEST_FILES) {
      const relFile = path.relative(SRC_ROOT, file)
      const text = readFileSync(file, "utf8")
      for (const hit of findCandidates(text, relFile)) {
        allHits.push(
          `${hit.file}:${hit.line}  ${hit.candidate}  -- break this with a space inside ` +
            "the brackets, e.g. `bg-[ hsl(var(--token)) ]`, per the convention recorded in " +
            "cbom-badge-contrast-guard.test.ts",
        )
      }
    }

    expect(allHits).toEqual([])
  })

  it("detection function is not vacuous in the other direction: it reports exactly one hit on a synthetic intact candidate", () => {
    // Built by concatenation, deliberately NOT as an intact literal -- if this guard's
    // own fixture were written as a real arbitrary-value class, it would itself be an
    // intact candidate inside a __tests__ file and could emit a junk CSS rule. A
    // future reader who "simplifies" this concatenation back into one string breaks
    // the build for a third time. Leave the pieces separate.
    const utilityPrefix = "bg" + "-"
    const openBracket = "["
    const innerValue = "hsl(var(--nonexistent-token))"
    const closeBracket = "]"
    const syntheticIntactClass = utilityPrefix + openBracket + innerValue + closeBracket

    const hits = findCandidates(syntheticIntactClass, "synthetic-fixture")

    expect(hits).toHaveLength(1)
    expect(hits[0].candidate).toBe(syntheticIntactClass)
  })
})
