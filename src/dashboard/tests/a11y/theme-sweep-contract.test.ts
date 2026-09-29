import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { THEMES } from "./baseline-diff.mjs"

// Phase 216 / HARNESS-01 / 216-CONTEXT.md D-16.
//
// This is the mechanical guard that keeps the harness, the npm scripts and both CI jobs
// from ever drifting apart on which themes are swept. Every assertion below derives its
// occurrence set from THEMES (the single allowlist in baseline-diff.mjs) at run time --
// never from a hardcoded 'light'/'dark' literal array in this file -- so adding a theme to
// THEMES without adding its scripts or CI steps fails here, not in a future incident report.
// This is the same run-time-source-scan idiom CLAUDE.md's § GSD state.* Verb Integrity
// records this project being bitten by omitting, applied here before a gap can form.

const PACKAGE_JSON_PATH = path.resolve(__dirname, "../../package.json")
const PACKAGE_JSON = JSON.parse(readFileSync(PACKAGE_JSON_PATH, "utf-8"))

const WORKFLOW_PATH = path.resolve(
  __dirname,
  "../../../../.github/workflows/dashboard-quality.yml",
)
const WORKFLOW_TEXT = readFileSync(WORKFLOW_PATH, "utf-8")

const RUN_A11Y_PATH = path.resolve(__dirname, "run-a11y.mjs")
const RUN_A11Y_SOURCE = readFileSync(RUN_A11Y_PATH, "utf-8")

const THEME_CONTEXT_PATH = path.resolve(
  __dirname,
  "../../src/components/theme-context.ts",
)
const THEME_CONTEXT_SOURCE = readFileSync(THEME_CONTEXT_PATH, "utf-8")

describe("theme-sweep contract — harness, scripts and CI cannot drift apart (216 D-16)", () => {
  it("THEMES is non-empty and carries at least two entries (vacuity guard)", () => {
    // A one-theme THEMES would make every assertion below pass trivially -- this is the
    // "what input would make this FAIL?" check named in 216-CONTEXT.md § Specific Ideas.
    expect(Array.isArray(THEMES)).toBe(true)
    expect(THEMES.length).toBeGreaterThanOrEqual(2)
  })

  it.each(THEMES)(
    "package.json declares a11y:check:%s and a11y:baseline:%s, each invoking A11Y_THEME=%s",
    (theme) => {
      const checkScript = PACKAGE_JSON.scripts[`a11y:check:${theme}`]
      const baselineScript = PACKAGE_JSON.scripts[`a11y:baseline:${theme}`]
      expect(checkScript, `missing npm script a11y:check:${theme}`).toBeTruthy()
      expect(baselineScript, `missing npm script a11y:baseline:${theme}`).toBeTruthy()
      expect(checkScript).toContain(`A11Y_THEME=${theme}`)
      expect(baselineScript).toContain(`A11Y_THEME=${theme}`)
    },
  )

  it.each(THEMES)(
    "dashboard-quality.yml names both npm run a11y:check:%s and npm run a11y:baseline:%s",
    (theme) => {
      // D-16's actual requirement, mechanically enforced: a theme with scripts but no CI
      // step is the exact green-gate-over-real-failures shape this milestone exists to fix.
      expect(
        WORKFLOW_TEXT,
        `dashboard-quality.yml has no "npm run a11y:check:${theme}" step`,
      ).toContain(`npm run a11y:check:${theme}`)
      expect(
        WORKFLOW_TEXT,
        `dashboard-quality.yml has no "npm run a11y:baseline:${theme}" step`,
      ).toContain(`npm run a11y:baseline:${theme}`)
    },
  )

  it("run-a11y.mjs's THEME_STORAGE_KEY literal equals theme-context.ts's exported constant (D-01)", () => {
    const harnessMatch = RUN_A11Y_SOURCE.match(
      /const THEME_STORAGE_KEY = ['"]([^'"]+)['"]/,
    )
    const contextMatch = THEME_CONTEXT_SOURCE.match(
      /export const THEME_STORAGE_KEY = ["']([^"']+)["']/,
    )
    expect(harnessMatch, "run-a11y.mjs has no THEME_STORAGE_KEY literal").not.toBeNull()
    expect(
      contextMatch,
      "theme-context.ts has no exported THEME_STORAGE_KEY constant",
    ).not.toBeNull()
    // FAILS if either copy is edited alone -- this is what makes the deliberate
    // duplication (run-a11y.mjs is .mjs and cannot import from theme-context.ts) safe.
    expect(harnessMatch![1]).toBe(contextMatch![1])
  })

  it("seeds the theme via page.evaluateOnNewDocument, never a forced classList or emulated media (D-01)", () => {
    expect(RUN_A11Y_SOURCE).toContain("page.evaluateOnNewDocument(")
    // The two mechanisms D-01 explicitly rejected, checked as an actual CALL rather than a
    // bare substring -- the harness's own header comment names `Emulation.setEmulatedMedia`
    // as the rejected alternative, so a bare `not.toContain("setEmulatedMedia")` would fail
    // against that documentation, not against a real regression. A future change that swaps
    // the mechanism without revisiting D-01 should fail here first.
    expect(RUN_A11Y_SOURCE).not.toMatch(/classList\.add\(\s*THEME\b/)
    expect(RUN_A11Y_SOURCE).not.toMatch(/\.setEmulatedMedia\(/)
  })

  it("refuses a non-dark theme on a non-default variant, loudly, citing D-03", () => {
    // Substrings per CLAUDE.md's grep-hygiene note, not a line count -- this asserts the
    // refusal guard exists and cites D-03 and exits, without pinning its exact wording.
    expect(RUN_A11Y_SOURCE).toContain("D-03")
    expect(RUN_A11Y_SOURCE).toContain("process.exit(1)")
    expect(RUN_A11Y_SOURCE).toContain("THEME !== 'dark'")
    // Confirm the three substrings live in the same guard region, not scattered
    // coincidentally across unrelated code -- the guard block is bounded by the REFUSED
    // console.error call and its immediate process.exit(1).
    const refusedIndex = RUN_A11Y_SOURCE.indexOf("REFUSED")
    expect(refusedIndex, "no REFUSED refusal message found").toBeGreaterThan(-1)
    const guardRegion = RUN_A11Y_SOURCE.slice(refusedIndex, refusedIndex + 400)
    expect(guardRegion).toContain("D-03")
    expect(guardRegion).toContain("process.exit(1)")
  })
})
