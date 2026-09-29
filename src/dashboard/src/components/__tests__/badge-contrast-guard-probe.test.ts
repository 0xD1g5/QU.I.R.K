/**
 * Mutation probe over the pure badge-contrast evaluator — Phase 215 plan 215-04 (RATCHET-04).
 *
 * WHY THIS FILE EXISTS. A guard nobody has seen fail is a guard nobody has tested. Plans
 * 215-01..03 built `badge-contrast-guard.test.ts` and its checked-in baseline, but nothing
 * in this repo had ever forced that guard red and watched it name the right thing. This
 * probe closes that gap by driving the pure `evaluatePairs()` evaluator directly, with
 * hand-built SYNTHETIC input.
 *
 * WHY SYNTHETIC INPUT IS POSSIBLE AT ALL. `badge-contrast-evaluator.ts` performs NO
 * filesystem I/O and imports NO vitest — every export is a pure function of its
 * arguments, the same architecture `tests/a11y/baseline-diff.mjs` states for itself at
 * its own :5-11 ("all reads and writes stay in run-a11y.mjs. Every export here is a pure
 * function of its arguments"). Purity is what makes fast, deterministic mutation testing
 * possible instead of a slow, flake-prone round-trip through real source files and a real
 * `index.css`.
 *
 * WHAT THIS PROBE DELIBERATELY DOES NOT DO. It never reads a real `.tsx` or `.css` file
 * and never mutates any real source file — every `file`, token name and hex value below is
 * fabricated and chosen not to collide with anything real. That means there is no
 * git-dirt window: nothing this file does can leave a real file edited, and nothing here
 * risks a probe-induced edit being accidentally committed. It also means the fixture
 * cannot flake when Phase 217 changes a real token's value, because it never reads one.
 *
 * BOTH RATCHET DIRECTIONS, PLUS A CONTROL AND THE THIRD DIRECTION. A probe that only
 * injects a brand-new failure proves half the gate — it says nothing about whether a
 * baselined entry can be silently widened without tripping anything. This file injects
 * both: a new sub-AA pair absent from the baseline (Injection A), and a baselined entry
 * whose live ratio has fallen below its recorded ceiling (Injection B). A third node
 * proves the evaluator is not simply failing everything (Control), and a fourth proves the
 * ratchet also demands deletion of an entry that has been fixed (the "fixed" direction) —
 * without it, this file would only prove non-worsening, not shrink-only.
 *
 * ALL FOUR TEST NODES ARE GREEN, BY DESIGN. This file is a positive test about negative
 * behaviour: it asserts the injected failures ARE caught, the same idiom the real guard's
 * own stale-entry check uses. The RED evidence roadmap SC#4 requires — "captured as
 * evidence rather than asserted in prose" — is NOT this file passing. It is produced
 * separately, by temporarily inverting one assertion here and by temporarily deleting a
 * real baseline entry from `badge-contrast-guard.test.ts`'s sibling JSON, and both
 * verbatim terminal captures live in `215-04-SUMMARY.md`, not in this file. A
 * `Self-Check: PASSED` line is a claim, not evidence — the verbatim red terminal output
 * is.
 */
import { describe, it, expect } from "vitest"
import { evaluatePairs, pairKey, type BadgePair } from "./badge-contrast-evaluator"

// Fabricated file/token names, chosen not to collide with anything real in this codebase.
// Do NOT derive these from a real token in `index.css` — a real token's value can change
// under Phase 217 and would make this probe flake for reasons unrelated to what it tests.
const FILE = "probe/synthetic.tsx"
const THEME = "probeTheme"

// Concrete hex pairs chosen so the resulting ratios are unambiguous and stable:
//   probe-bg-new       vs white ~= 1.61:1  -- well below AA_NORMAL_TEXT (4.5)
//   probe-bg-worsened  vs white ~= 2.10:1  -- well below AA_NORMAL_TEXT (4.5)
//   probe-bg-control   vs white ~= 1.61:1  -- same hex as probe-bg-new, deliberately
//   probe-bg-fixed     vs white ~= 17.40:1 -- well above AA_NORMAL_TEXT (4.5)
const TOKENS: Record<string, Record<string, string>> = {
  [THEME]: {
    "probe-bg-new": "#cccccc",
    "probe-bg-worsened": "#b3b3b3",
    "probe-bg-control": "#cccccc",
    "probe-bg-fixed": "#1a1a1a",
  },
}

function syntheticPair(bgToken: string): BadgePair {
  return { file: FILE, bgToken, fgSpec: "white" }
}

describe("badge-contrast mutation probe (RATCHET-04) -- synthetic input, no filesystem I/O", () => {
  it("Injection A (D-19a): a new sub-AA pair absent from the baseline is caught as kind 'new'", () => {
    const pair = syntheticPair("probe-bg-new")
    const key = pairKey(pair, THEME)

    const failures = evaluatePairs([pair], TOKENS, {})

    expect(failures).toHaveLength(1)
    expect(failures[0].kind).toBe("new")
    expect(failures[0].key).toBe(key)
    expect(failures[0].detail).toContain(FILE)
    expect(failures[0].detail).toContain("probe-bg-new")
    expect(failures[0].detail).toMatch(/1\.6\d:1/)
  })

  it("Injection B (D-19b): a baselined entry silently widened to a worse ratio is caught as kind 'worsened'", () => {
    const pair = syntheticPair("probe-bg-worsened")
    const key = pairKey(pair, THEME)
    // Baseline recorded a ceiling of 3.50:1; the live synthetic measurement (~2.10:1) has
    // since fallen well below it -- the exact "silently widened" shape D-19b names.
    const baseline = {
      [key]: {
        ratio: 3.5,
        why: "synthetic probe fixture -- baseline recorded a ceiling of 3.50:1 that the live measurement has since fallen below",
      },
    }

    const failures = evaluatePairs([pair], TOKENS, baseline)

    expect(failures).toHaveLength(1)
    expect(failures[0].kind).toBe("worsened")
    expect(failures[0].key).toBe(key)
    expect(failures[0].detail).toContain(FILE)
    expect(failures[0].detail).toContain("probe-bg-worsened")
  })

  it("Control: a baselined entry at its actual, unchanged ratio produces zero failures", () => {
    // Without this node the first two nodes would be tautologies -- they would pass
    // just as well against an evaluator that fails every pair it is given. This node is
    // what proves the evaluator can also stay quiet.
    const pair = syntheticPair("probe-bg-control")
    const key = pairKey(pair, THEME)
    const baseline = {
      [key]: {
        ratio: 1.61,
        why: "synthetic probe fixture -- baseline recorded exactly the live measured ratio, unchanged",
      },
    }

    const failures = evaluatePairs([pair], TOKENS, baseline)

    expect(failures).toHaveLength(0)
  })

  it("Third ratchet direction: a baselined pair that now clears AA is caught as kind 'fixed'", () => {
    // This is the assertion that makes the ratchet shrink-only rather than merely
    // non-worsening: a baselined pair whose live ratio has crossed back above
    // AA_NORMAL_TEXT must be flagged for its entry's deletion, not silently accepted.
    const pair = syntheticPair("probe-bg-fixed")
    const key = pairKey(pair, THEME)
    const baseline = {
      [key]: {
        ratio: 3.0,
        why: "synthetic probe fixture -- baseline recorded a sub-AA ratio the live measurement has since cleared",
      },
    }

    const failures = evaluatePairs([pair], TOKENS, baseline)

    expect(failures).toHaveLength(1)
    expect(failures[0].kind).toBe("fixed")
    expect(failures[0].key).toBe(key)
    expect(failures[0].detail.toLowerCase()).toContain("delete")
  })
})
